#!/usr/bin/env python3
"""Verify CACE v3.30 qualification evidence against external/source trust anchors.

This verifier is standard-library-only and separate from Lean and the attestation
producer. It re-derives proof-contract identity, audited Lean source identity,
resolved Lake-manifest identity, audit-source identity, and (when required by the
proof contract) every executable-source binding from repository bytes.

A PASS verifies recorded qualification evidence; it does not itself prove a theorem
or establish that runtime scientific inputs satisfy theorem hypotheses.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import tempfile
from typing import Any, Iterator, Mapping
import zipfile

ATTESTATION = "cace_continuum_qualification_attestation.json"
METADATA = "v330_lean_environment_metadata.json"
AXIOM_AUDIT = "v330_kernel_axiom_audit.json"
RESOLVED_MANIFEST = "v330_resolved_lake_manifest.json"
CLAIM_ID = "cace.v330.continuum-proof-strengthening"
ATTESTATION_SCHEMA = "cace-continuum-qualification-attestation-v2"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_GIT_COMMIT = re.compile(r"^[0-9a-f]{40}$")


class SourceBindingVerificationError(RuntimeError):
    """Raised when qualification evidence cannot be tied to source/external anchors."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SourceBindingVerificationError(message)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def require_sha256(value: Any, field: str) -> str:
    require(isinstance(value, str), f"{field} must be a string")
    result = value.strip().lower()
    require(bool(_SHA256.fullmatch(result)), f"{field} must be lowercase 64-hex SHA-256")
    return result


def require_commit(value: Any, field: str) -> str:
    require(isinstance(value, str), f"{field} must be a string")
    result = value.strip().lower()
    require(bool(_GIT_COMMIT.fullmatch(result)), f"{field} must be lowercase 40-hex Git commit")
    return result


def require_positive_int(value: Any, field: str) -> int:
    require(
        isinstance(value, int) and not isinstance(value, bool) and value > 0,
        f"{field} must be a positive integer",
    )
    return value


def load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SourceBindingVerificationError(f"cannot load {label}: {exc}") from exc
    require(isinstance(value, dict), f"{label} must be a JSON object")
    return value


def compact_identity_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def safe_relative(value: Any, *, suffix: str | None = None) -> str:
    require(isinstance(value, str) and value, "source path must be non-empty")
    path = PurePosixPath(value)
    require(
        not path.is_absolute() and ".." not in path.parts and bool(path.name),
        f"unsafe relative path: {value!r}",
    )
    if suffix is not None:
        require(path.suffix == suffix, f"path must end in {suffix}: {value!r}")
    return path.as_posix()


def string_list(value: Any, field: str) -> tuple[str, ...]:
    require(isinstance(value, list), f"{field} must be an array")
    require(
        all(isinstance(item, str) and item for item in value),
        f"{field} must contain non-empty strings",
    )
    result = tuple(value)
    require(len(result) == len(set(result)), f"{field} contains duplicates")
    return result


def normalized_contract(raw: Mapping[str, Any]) -> dict[str, Any]:
    required = (
        "contract_id",
        "claim_id",
        "formal_system",
        "build_target",
        "toolchain_file",
        "dependency_pins",
        "endpoint_theorems",
        "audited_source_files",
        "allowed_axioms",
        "required_checks",
        "nonclaims",
        "theorem_dependency_metadata",
    )
    for field in required:
        require(field in raw, f"proof contract missing {field}")
    result = {field: raw[field] for field in required}
    bindings = raw.get("executable_bindings", [])
    require(isinstance(bindings, list), "proof contract executable_bindings must be an array")
    if bindings:
        result["executable_bindings"] = bindings
    return result


def load_contract(path: Path, contract_id: str) -> tuple[dict[str, Any], str]:
    registry = load_json(path, "proof-contract registry")
    contracts = registry.get("contracts")
    require(isinstance(contracts, list), "proof-contract registry contracts must be an array")
    matches = [
        item
        for item in contracts
        if isinstance(item, Mapping) and item.get("contract_id") == contract_id
    ]
    require(len(matches) == 1, f"expected exactly one proof contract {contract_id!r}")
    contract = normalized_contract(matches[0])
    return contract, sha256_bytes(compact_identity_bytes(contract))


def source_bundle_sha256(formal_dir: Path, source_files: tuple[str, ...]) -> str:
    root = formal_dir.resolve()
    digest = hashlib.sha256()
    for relative in source_files:
        relative = safe_relative(relative, suffix=".lean")
        path = (root / PurePosixPath(relative)).resolve()
        try:
            path.relative_to(root)
        except ValueError as exc:
            raise SourceBindingVerificationError(
                f"audited source escapes formal directory: {relative}"
            ) from exc
        require(path.is_file(), f"audited source file is missing: {relative}")
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def executable_source_bundle_manifest(
    repo_root: Path,
    source_files: tuple[str, ...],
) -> dict[str, Any]:
    root = repo_root.resolve()
    canonical = tuple(sorted(safe_relative(item) for item in source_files))
    require(bool(canonical), "executable binding source_files must not be empty")
    require(
        len(canonical) == len(set(canonical)),
        "executable binding source_files contains duplicates",
    )
    files: list[dict[str, Any]] = []
    for relative in canonical:
        path = (root / PurePosixPath(relative)).resolve()
        try:
            path.relative_to(root)
        except ValueError as exc:
            raise SourceBindingVerificationError(
                f"executable source escapes repository root: {relative}"
            ) from exc
        require(path.is_file(), f"executable source file is missing: {relative}")
        data = path.read_bytes()
        files.append(
            {
                "path": relative,
                "sha256": sha256_bytes(data),
                "size": len(data),
            }
        )
    return {
        "algorithm": "cace-executable-source-bundle-v1",
        "files": files,
    }


def executable_source_bundle_sha256(
    repo_root: Path,
    source_files: tuple[str, ...],
) -> str:
    return sha256_bytes(
        compact_identity_bytes(executable_source_bundle_manifest(repo_root, source_files))
    )


def verify_executable_bindings(
    contract: Mapping[str, Any],
    *,
    repo_root: Path,
) -> list[dict[str, Any]]:
    checks = string_list(contract.get("required_checks"), "contract.required_checks")
    raw_bindings = contract.get("executable_bindings", [])
    require(isinstance(raw_bindings, list), "proof contract executable_bindings must be an array")

    check_required = "executable-source-binding" in checks
    if raw_bindings and not check_required:
        raise SourceBindingVerificationError(
            "proof contract contains executable bindings without executable-source-binding check"
        )
    if check_required:
        require(bool(raw_bindings), "executable-source-binding check requires executable bindings")

    reports: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in raw_bindings:
        require(isinstance(raw, Mapping), "executable binding must be an object")
        require(
            set(raw) == {"module_id", "source_files", "source_bundle_sha256"},
            "executable binding keys mismatch",
        )
        module_id = raw.get("module_id")
        require(
            isinstance(module_id, str) and bool(module_id.strip()),
            "executable binding module_id must be non-empty",
        )
        module_id = module_id.strip()
        require(module_id not in seen, f"duplicate executable binding module_id: {module_id}")
        seen.add(module_id)
        source_files = string_list(raw.get("source_files"), f"{module_id}.source_files")
        expected = require_sha256(
            raw.get("source_bundle_sha256"),
            f"{module_id}.source_bundle_sha256",
        )
        actual = executable_source_bundle_sha256(repo_root, source_files)
        require(
            actual == expected,
            f"executable source bundle differs from proof contract for {module_id}",
        )
        reports.append(
            {
                "module_id": module_id,
                "source_files": list(sorted(source_files)),
                "source_bundle_sha256": actual,
            }
        )
    return sorted(reports, key=lambda item: item["module_id"])


def _default_repo_root(proof_contracts: Path) -> Path:
    resolved = proof_contracts.resolve()
    if (
        resolved.name == "proof_contracts.json"
        and resolved.parent.name == "data"
        and resolved.parent.parent.name == "cace_studio"
    ):
        return resolved.parent.parent.parent
    return resolved.parent


def verify_source_binding(
    root: Path,
    *,
    formal_dir: Path,
    proof_contracts: Path,
    expected_attestation_sha256: str,
    expected_git_commit: str,
    expected_workflow_run_id: int,
    expected_workflow_run_attempt: int,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    expected_attestation = require_sha256(
        expected_attestation_sha256, "expected_attestation_sha256"
    )
    expected_commit = require_commit(expected_git_commit, "expected_git_commit")
    expected_run = require_positive_int(
        expected_workflow_run_id, "expected_workflow_run_id"
    )
    expected_attempt = require_positive_int(
        expected_workflow_run_attempt, "expected_workflow_run_attempt"
    )

    att_path = root / ATTESTATION
    meta_path = root / METADATA
    audit_path = root / AXIOM_AUDIT
    manifest_path = root / RESOLVED_MANIFEST
    for path in (att_path, meta_path, audit_path, manifest_path):
        require(path.is_file(), f"missing source-bound qualification file: {path.name}")

    att_bytes = att_path.read_bytes()
    actual_attestation = sha256_bytes(att_bytes)
    require(
        actual_attestation == expected_attestation,
        "qualification attestation differs from external SHA-256 trust anchor",
    )
    att = load_json(att_path, "qualification attestation")
    meta = load_json(meta_path, "Lean theorem metadata")
    audit = load_json(audit_path, "kernel axiom audit")

    require(
        att.get("attestation_schema") == ATTESTATION_SCHEMA,
        "unsupported qualification attestation schema",
    )
    require(att.get("status") == "PASS", "qualification attestation status must be PASS")
    require(
        att.get("current_head_required") is True,
        "qualification attestation must require current head",
    )
    require(att.get("claim_id") == CLAIM_ID, "unexpected qualification claim_id")
    require(
        require_commit(att.get("git_commit"), "attestation.git_commit") == expected_commit,
        "qualification attestation Git commit differs from external trust anchor",
    )
    require(
        require_positive_int(att.get("workflow_run_id"), "attestation.workflow_run_id")
        == expected_run,
        "qualification workflow_run_id differs from external trust anchor",
    )
    require(
        require_positive_int(
            att.get("workflow_run_attempt"), "attestation.workflow_run_attempt"
        )
        == expected_attempt,
        "qualification workflow_run_attempt differs from external trust anchor",
    )
    if att.get("qualification_system") == "github-actions":
        require(
            str(att.get("qualification_run_id")) == str(expected_run),
            "qualification_run_id/workflow_run_id mismatch",
        )

    contract_id = str(att.get("proof_contract_id", ""))
    require(bool(contract_id), "attestation proof_contract_id must be non-empty")
    contract, contract_sha = load_contract(proof_contracts, contract_id)
    require(contract.get("claim_id") == CLAIM_ID, "proof contract claim_id mismatch")
    require(
        require_sha256(
            att.get("proof_contract_sha256"), "attestation.proof_contract_sha256"
        )
        == contract_sha,
        "proof-contract SHA-256 differs from canonical contract",
    )

    source_files = string_list(
        att.get("audited_source_files"), "attestation.audited_source_files"
    )
    require(
        source_files
        == string_list(contract.get("audited_source_files"), "contract.audited_source_files"),
        "attestation audited sources differ from canonical proof contract",
    )
    checks = string_list(
        att.get("qualification_checks"), "attestation.qualification_checks"
    )
    require(
        checks == string_list(contract.get("required_checks"), "contract.required_checks"),
        "attestation qualification checks differ from canonical proof contract",
    )
    require(
        "independent-source-bound-verification" in checks,
        "proof contract does not require independent source-bound verification",
    )

    actual_source_bundle = source_bundle_sha256(formal_dir, source_files)
    require(
        actual_source_bundle
        == require_sha256(
            att.get("audited_source_bundle_sha256"),
            "attestation.audited_source_bundle_sha256",
        ),
        "audited formal source bundle differs from attestation",
    )

    executable_reports = verify_executable_bindings(
        contract,
        repo_root=(repo_root or _default_repo_root(proof_contracts)),
    )

    actual_manifest = sha256_bytes(manifest_path.read_bytes())
    require(
        actual_manifest
        == require_sha256(
            att.get("lake_manifest_sha256"), "attestation.lake_manifest_sha256"
        ),
        "resolved Lake manifest differs from attestation",
    )
    live_manifest = formal_dir / "lake-manifest.json"
    if live_manifest.is_file():
        require(
            sha256_bytes(live_manifest.read_bytes()) == actual_manifest,
            "artifact Lake manifest differs from live qualification manifest",
        )

    actual_meta = sha256_bytes(meta_path.read_bytes())
    actual_audit = sha256_bytes(audit_path.read_bytes())
    require(
        actual_meta
        == require_sha256(
            att.get("lean_environment_metadata_sha256"),
            "attestation.lean_environment_metadata_sha256",
        ),
        "Lean theorem metadata differs from attestation",
    )
    require(
        actual_audit
        == require_sha256(
            att.get("kernel_axiom_audit_sha256"),
            "attestation.kernel_axiom_audit_sha256",
        ),
        "kernel axiom audit differs from attestation",
    )
    require(meta.get("git_commit") == expected_commit, "Lean theorem metadata Git commit mismatch")
    require(
        meta.get("proof_contract_sha256") == contract_sha,
        "Lean theorem metadata proof-contract hash mismatch",
    )
    require(
        meta.get("kernel_axiom_audit_sha256") == actual_audit,
        "Lean theorem metadata audit hash mismatch",
    )

    audit_source = safe_relative(audit.get("audit_source"), suffix=".lean")
    require(
        audit_source in set(source_files),
        "kernel audit source is outside the audited source bundle",
    )
    audit_source_path = (formal_dir.resolve() / PurePosixPath(audit_source)).resolve()
    try:
        audit_source_path.relative_to(formal_dir.resolve())
    except ValueError as exc:
        raise SourceBindingVerificationError(
            "kernel audit source escapes formal directory"
        ) from exc
    require(audit_source_path.is_file(), f"kernel audit source is missing: {audit_source}")
    require(
        sha256_bytes(audit_source_path.read_bytes())
        == require_sha256(
            audit.get("audit_source_sha256"), "kernel audit source SHA-256"
        ),
        "kernel audit source digest differs from audited source bytes",
    )

    return {
        "schema": "cace-v330-independent-source-binding-verification-v1",
        "status": "PASS",
        "proof_effect": "verification-of-recorded-evidence-only",
        "claim_id": CLAIM_ID,
        "git_commit": expected_commit,
        "workflow_run_id": expected_run,
        "workflow_run_attempt": expected_attempt,
        "proof_contract_id": contract_id,
        "proof_contract_sha256": contract_sha,
        "attestation_sha256": actual_attestation,
        "audited_source_bundle_sha256": actual_source_bundle,
        "executable_bindings": executable_reports,
        "lake_manifest_sha256": actual_manifest,
        "lean_environment_metadata_sha256": actual_meta,
        "kernel_axiom_audit_sha256": actual_audit,
    }


@contextmanager
def bundle_root(path: Path) -> Iterator[Path]:
    if path.is_dir():
        yield path
        return
    require(
        path.is_file() and zipfile.is_zipfile(path),
        "bundle must be a directory or ZIP archive",
    )
    with tempfile.TemporaryDirectory(prefix="cace-source-binding-verify-") as tmp:
        root = Path(tmp)
        root_resolved = root.resolve()
        with zipfile.ZipFile(path) as archive:
            for info in archive.infolist():
                target = (root / info.filename).resolve()
                require(
                    target == root_resolved or root_resolved in target.parents,
                    f"unsafe ZIP member path: {info.filename}",
                )
            archive.extractall(root)
        yield root


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--formal-dir", type=Path, required=True)
    parser.add_argument("--proof-contracts", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path)
    parser.add_argument("--expected-attestation-sha256", required=True)
    parser.add_argument("--expected-git-commit", required=True)
    parser.add_argument("--expected-workflow-run-id", type=int, required=True)
    parser.add_argument("--expected-workflow-run-attempt", type=int, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        with bundle_root(args.bundle) as root:
            report = verify_source_binding(
                root,
                formal_dir=args.formal_dir,
                proof_contracts=args.proof_contracts,
                repo_root=args.repo_root,
                expected_attestation_sha256=args.expected_attestation_sha256,
                expected_git_commit=args.expected_git_commit,
                expected_workflow_run_id=args.expected_workflow_run_id,
                expected_workflow_run_attempt=args.expected_workflow_run_attempt,
            )
        code = 0
    except (SourceBindingVerificationError, OSError, ValueError, zipfile.BadZipFile) as exc:
        report = {
            "schema": "cace-v330-independent-source-binding-verification-v1",
            "status": "FAIL",
            "error_type": type(exc).__name__,
            "error": str(exc),
        }
        code = 1
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
        args.output.with_suffix(args.output.suffix + ".sha256").write_text(
            f"{sha256_bytes(rendered.encode())}  {args.output.name}\n",
            encoding="utf-8",
        )
    print(rendered, end="")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
