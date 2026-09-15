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
                # Local filesystem paths are intentionally excluded from the
                # content identity. artifact_id is the portable logical name.
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("registry", help="List module contracts; metadata is not executed evidence")

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

        if args.command == "registry":
            registry = build_registry()
            payload = {
                "cli_schema": 1,
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
