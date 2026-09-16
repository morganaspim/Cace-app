"""Headless, versioned JSON interface for local tools and AI agents."""
from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys
from typing import Any

from .app import build_registry
from .core.evidence_ledger import (
    EvidenceArtifact,
    EvidenceBundle,
    EvidenceLedgerError,
    bundle_from_payload,
    verify_bundle,
)
from .core.executor import GraphExecutor
from .core.proof_explorer import ProofExplorer
from .core.qualification_attestation import load_qualification_attestation
from .core.report import run_report
from .core.reproducibility import drift_report, reproducibility_manifest
from .core.serialization import load_experiment


def _render(payload: Any) -> str:
    return json.dumps(
        payload,
        indent=2,
        sort_keys=True,
        default=repr,
        allow_nan=False,
    ) + "\n"


def _key_value(spec: str, *, label: str) -> tuple[str, str]:
    if "=" not in spec:
        raise ValueError(f"{label} must use KEY=VALUE syntax: {spec!r}")
    key, value = spec.split("=", 1)
    key = key.strip()
    if not key:
        raise ValueError(f"{label} key must be non-empty")
    return key, value


def _bindings(specs: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for spec in specs:
        key, value = _key_value(spec, label="binding")
        if key in result:
            raise ValueError(f"duplicate binding key: {key}")
        result[key] = value
    return result


def _artifact_inputs(specs: list[str]) -> tuple[tuple[EvidenceArtifact, ...], dict[str, bytes]]:
    artifacts: list[EvidenceArtifact] = []
    byte_map: dict[str, bytes] = {}
    for spec in specs:
        artifact_id, path_text = _key_value(spec, label="artifact")
        if artifact_id in byte_map:
            raise ValueError(f"duplicate artifact id: {artifact_id}")
        path = Path(path_text)
        data = path.read_bytes()
        artifacts.append(
            EvidenceArtifact.from_bytes(
                artifact_id,
                data,
                role="artifact",
                media_type="application/octet-stream",
                path=None,
            )
        )
        byte_map[artifact_id] = data
    return tuple(artifacts), byte_map


def _load_bundle_document(path: Path) -> tuple[EvidenceBundle, str | None]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise EvidenceLedgerError("bundle document must be a JSON object")
    if "bundle" in document:
        allowed = {
            "cli_schema",
            "command",
            "proof_effect",
            "bundle_sha256",
            "bundle",
        }
        extra = sorted(set(document) - allowed)
        if extra:
            raise EvidenceLedgerError(f"bundle document has unknown keys: {extra}")
        if document.get("proof_effect") != "none":
            raise EvidenceLedgerError("bundle document proof_effect must be 'none'")
        bundle = bundle_from_payload(document["bundle"])
        declared = document.get("bundle_sha256")
        if not isinstance(declared, str):
            raise EvidenceLedgerError("bundle document is missing bundle_sha256")
        if declared != bundle.bundle_sha256:
            raise EvidenceLedgerError(
                "bundle document SHA-256 does not match its canonical bundle payload"
            )
        return bundle, declared
    return bundle_from_payload(document), None


def _module_registry_payload() -> dict[str, Any]:
    registry = build_registry()
    return {
        "cli_schema": 1,
        "command": "modules-list",
        "metadata_is_verification_evidence": False,
        "modules": [
            {
                "metadata": asdict(cls.metadata),
                "inputs": [asdict(p) for p in cls.inputs],
                "outputs": [asdict(p) for p in cls.outputs],
                "parameters": [asdict(p) for p in cls.parameters],
                "declared_proof_status": cls.proof_status.to_dict(),
            }
            for cls in sorted(registry.classes(), key=lambda cls: cls.metadata.module_id)
        ],
    }


def _claim_summary(view) -> dict[str, Any]:
    return {
        "claim_id": view.claim_id,
        "statement": view.statement,
        "evidence_ceiling": view.evidence_ceiling,
        "qualification_state": view.qualification_state,
        "qualification_source": view.qualification_source,
        "current_head_qualified": view.current_head_qualified,
        "proof_contract_id": view.proof_contract_id,
        "proof_contract_sha256": view.proof_contract_sha256,
        "theorem_dependency_metadata_state": view.theorem_dependency_metadata_state,
        "attested_commit": view.attested_commit,
        "proof_artifact_sha256": view.proof_artifact_sha256,
        "blockers": list(view.blockers),
    }


def _add_qualification_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--qualification-attestation",
        type=Path,
        help=(
            "External exact-head qualification JSON. Requires both --qualification-sha256 "
            "and --current-head; the artifact alone is never trusted."
        ),
    )
    parser.add_argument(
        "--qualification-sha256",
        help="Expected SHA-256 for the exact attestation bytes from an external trust channel.",
    )
    parser.add_argument(
        "--current-head",
        help="Exact 40-hex Git commit that must be attested by the external qualification artifact.",
    )


def _proof_explorer(args: argparse.Namespace) -> ProofExplorer:
    path = getattr(args, "qualification_attestation", None)
    digest = getattr(args, "qualification_sha256", None)
    current_head = getattr(args, "current_head", None)
    supplied = [path is not None, digest is not None, current_head is not None]
    if any(supplied) and not all(supplied):
        raise ValueError(
            "external qualification requires --qualification-attestation, "
            "--qualification-sha256, and --current-head together"
        )
    if path is None:
        return ProofExplorer()
    qualification = load_qualification_attestation(
        path,
        expected_git_commit=current_head,
        expected_artifact_sha256=digest,
    )
    return ProofExplorer(qualifications=(qualification,))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("registry", help="Compatibility alias for `modules list`")

    modules = sub.add_parser("modules", help="Inspect module contracts without executing them")
    modules_sub = modules.add_subparsers(dest="modules_command", required=True)
    modules_list = modules_sub.add_parser("list", help="List module contracts")
    modules_list.add_argument("--output", type=Path)

    claims = sub.add_parser("claims", help="Inspect canonical claim truth state")
    claims_sub = claims.add_subparsers(dest="claims_command", required=True)
    claims_list = claims_sub.add_parser("list", help="List canonical claims")
    claims_list.add_argument("--output", type=Path)
    _add_qualification_args(claims_list)
    claims_show = claims_sub.add_parser("show", help="Show one canonical claim and its proof bindings")
    claims_show.add_argument("claim_id")
    claims_show.add_argument("--output", type=Path)
    _add_qualification_args(claims_show)

    proofs = sub.add_parser("proofs", help="Inspect ProofContract/ProofLedger qualification state")
    proofs_sub = proofs.add_subparsers(dest="proofs_command", required=True)
    proofs_status = proofs_sub.add_parser("status", help="Show fail-closed qualification status for all claims")
    proofs_status.add_argument("--output", type=Path)
    _add_qualification_args(proofs_status)
    proofs_show = proofs_sub.add_parser("show", help="Show proof state for one canonical claim")
    proofs_show.add_argument("claim_id")
    proofs_show.add_argument("--output", type=Path)
    _add_qualification_args(proofs_show)

    run = sub.add_parser("run", help="Execute a .cace experiment and emit its evidence report")
    run.add_argument("experiment", type=Path)
    run.add_argument("--seed", type=int, default=0)
    run.add_argument("--output", type=Path)

    fingerprint = sub.add_parser(
        "fingerprint",
        help="Emit deterministic content identities for a .cace experiment; hashes are not evidence",
    )
    fingerprint.add_argument("experiment", type=Path)
    fingerprint.add_argument("--output", type=Path)

    compare = sub.add_parser(
        "compare",
        help="Compare two .cace files and classify semantic versus layout/presentation drift",
    )
    compare.add_argument("expected", type=Path)
    compare.add_argument("actual", type=Path)
    compare.add_argument("--output", type=Path)

    evidence_bundle = sub.add_parser(
        "evidence-bundle",
        help="Build a provenance-only content-addressed bundle from exact local files",
    )
    evidence_bundle.add_argument(
        "--artifact",
        action="append",
        default=[],
        metavar="ID=PATH",
        help="Portable logical artifact ID and local source path; repeat for each artifact",
    )
    evidence_bundle.add_argument(
        "--bind",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Context binding such as claim_id or git_commit; repeat as needed",
    )
    evidence_bundle.add_argument("--note", action="append", default=[])
    evidence_bundle.add_argument("--output", type=Path)

    evidence_verify = sub.add_parser(
        "evidence-verify",
        help="Verify a CACE evidence bundle; provenance integrity is not mathematical proof",
    )
    evidence_verify.add_argument("bundle", type=Path)
    evidence_verify.add_argument(
        "--artifact",
        action="append",
        default=[],
        metavar="ID=PATH",
        help="Exact artifact bytes to verify; must match the bundle ID set",
    )
    evidence_verify.add_argument(
        "--manifest-only",
        action="store_true",
        help="Verify only serialized manifests/root/digest, not artifact bytes",
    )
    evidence_verify.add_argument("--output", type=Path)

    args = parser.parse_args(argv)
    try:
        output_path: Path | None = getattr(args, "output", None)

        if args.command == "registry" or (
            args.command == "modules" and args.modules_command == "list"
        ):
            payload = _module_registry_payload()
            status = 0
        elif args.command == "claims":
            explorer = _proof_explorer(args)
            if args.claims_command == "list":
                views = explorer.all_claims()
                payload = {
                    "cli_schema": 1,
                    "command": "claims-list",
                    "proof_effect": "none",
                    "metadata_is_verification_evidence": False,
                    "claims": [_claim_summary(view) for view in views],
                }
            else:
                view = explorer.claim_view(args.claim_id)
                payload = {
                    "cli_schema": 1,
                    "command": "claims-show",
                    "proof_effect": "none",
                    "metadata_is_verification_evidence": False,
                    "claim": view.to_dict(),
                }
            status = 0
        elif args.command == "proofs":
            explorer = _proof_explorer(args)
            if args.proofs_command == "status":
                views = explorer.all_claims()
                state_counts: dict[str, int] = {}
                for view in views:
                    state_counts[view.qualification_state] = state_counts.get(view.qualification_state, 0) + 1
                payload = {
                    "cli_schema": 1,
                    "command": "proofs-status",
                    "proof_effect": "none",
                    "qualification_is_derived_fail_closed": True,
                    "all_current_head_qualified": bool(views) and all(
                        view.current_head_qualified for view in views
                    ),
                    "state_counts": state_counts,
                    "claims": [_claim_summary(view) for view in views],
                    "note": (
                        "This is a read-only canonical status view. It never mutates source truth. "
                        "A current-head PASS may come from matching static registry/ledger state or "
                        "from an externally supplied content-addressed qualification artifact whose "
                        "bytes, exact commit, ProofContract, endpoints, pins and checks all validate."
                    ),
                }
            else:
                view = explorer.claim_view(args.claim_id)
                payload = {
                    "cli_schema": 1,
                    "command": "proofs-show",
                    "proof_effect": "none",
                    "qualification_is_derived_fail_closed": True,
                    "proof": view.to_dict(),
                }
            status = 0
        elif args.command == "run":
            registry = build_registry()
            experiment = load_experiment(args.experiment)
            result = GraphExecutor(registry).run(experiment, seed=args.seed)
            payload = run_report(result, experiment.name)
            payload["cli_schema"] = 1
            payload["seed"] = args.seed
            states = [
                record.state.value
                for records in result.verification.values()
                for record in records
            ]
            status = 1 if "fail" in states else (0 if result.all_verifiers_passed else 3)
            payload["cli_exit_code"] = status
        elif args.command == "fingerprint":
            registry = build_registry()
            experiment = load_experiment(args.experiment)
            payload = {
                "cli_schema": 1,
                "command": "fingerprint",
                "experiment": str(args.experiment),
                "manifest": reproducibility_manifest(experiment, registry),
            }
            status = 0
        elif args.command == "compare":
            expected = load_experiment(args.expected)
            actual = load_experiment(args.actual)
            payload = {
                "cli_schema": 1,
                "command": "compare",
                "expected": str(args.expected),
                "actual": str(args.actual),
                "drift": drift_report(expected, actual),
            }
            status = 0
        elif args.command == "evidence-bundle":
            if not args.artifact:
                raise ValueError("evidence-bundle requires at least one --artifact ID=PATH")
            artifacts, byte_map = _artifact_inputs(args.artifact)
            bundle = EvidenceBundle(
                artifacts=artifacts,
                bindings=_bindings(args.bind),
                notes=tuple(args.note),
            )
            verify_bundle(bundle, artifact_bytes=byte_map)
            payload = {
                "cli_schema": 1,
                "command": "evidence-bundle",
                "proof_effect": "none",
                "bundle_sha256": bundle.bundle_sha256,
                "bundle": bundle.payload(),
            }
            status = 0
        else:
            bundle, _ = _load_bundle_document(args.bundle)
            if args.manifest_only:
                if args.artifact:
                    raise ValueError(
                        "--artifact cannot be combined with --manifest-only; "
                        "remove --manifest-only to verify exact bytes"
                    )
                digest = verify_bundle(bundle)
                scope = "manifest-only"
            else:
                if not args.artifact:
                    raise ValueError(
                        "evidence-verify requires --artifact ID=PATH for every artifact "
                        "unless --manifest-only is explicitly requested"
                    )
                _, byte_map = _artifact_inputs(args.artifact)
                digest = verify_bundle(bundle, artifact_bytes=byte_map)
                scope = "manifest-and-exact-bytes"
            payload = {
                "cli_schema": 1,
                "command": "evidence-verify",
                "verification_scope": scope,
                "proof_effect": "none",
                "bundle_sha256": digest,
                "merkle_root_sha256": bundle.merkle_root_sha256,
                "valid": True,
                "note": "Integrity/provenance verification does not establish mathematical truth.",
            }
            status = 0

        rendered = _render(payload)
        if output_path:
            output_path.write_text(rendered, encoding="utf-8")
        else:
            sys.stdout.write(rendered)
        return status
    except Exception as exc:
        sys.stderr.write(
            json.dumps(
                {
                    "cli_schema": 1,
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                }
            )
            + "\n"
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
