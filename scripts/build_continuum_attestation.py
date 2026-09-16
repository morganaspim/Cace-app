#!/usr/bin/env python3
"""Build a fail-closed, content-addressed continuum qualification attestation.

The attestation is created only after a successful exact-head Lean build, kernel
axiom audit, and Lean.Environment theorem metadata export. It binds those dynamic
artifacts to the canonical ProofContract, audited source bytes, resolved Lake
manifest, exact Git commit, pinned Lean/Mathlib identity, and qualification-run
provenance. The JSON itself is the proof artifact; its SHA-256 is written beside it.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any, Mapping

ATTESTATION_SCHEMA = "cace-continuum-qualification-attestation-v2"
CLAIM_ID = "cace.v330.continuum-proof-strengthening"
QUALIFICATION_SYSTEM = "github-actions"
CACHE_POLICY = (
    "Pinned Lean/toolchain state and exact-pin dependencies may be reused only as inputs; "
    "CACE project build outputs, kernel audit results, theorem metadata, and attestations "
    "are regenerated in the isolated exact-head qualification run."
)


class AttestationError(RuntimeError):
    """Raised when qualification evidence cannot be bound without ambiguity."""


def canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            separators=(",", ": "),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def is_hex(value: str, length: int) -> bool:
    return len(value) == length and all(char in "0123456789abcdef" for char in value.lower())


def require_sha256(value: str, field: str) -> str:
    result = str(value).strip().lower()
    if not is_hex(result, 64):
        raise AttestationError(f"{field} must be a 64-hex SHA-256")
    return result


def require_commit(value: str, field: str = "git_commit") -> str:
    result = str(value).strip().lower()
    if not is_hex(result, 40):
        raise AttestationError(f"{field} must be a 40-hex Git commit")
    return result


def require_nonempty(value: Any, field: str) -> str:
    result = str(value).strip()
    if not result:
        raise AttestationError(f"{field} must be non-empty")
    return result


def command_output(command: list[str], *, cwd: Path | None = None) -> str:
    try:
        return subprocess.check_output(command, cwd=cwd, text=True).strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise AttestationError(f"failed command {command!r}: {exc}") from exc


def audited_source_bundle_sha256(formal_dir: Path, source_files: tuple[str, ...]) -> str:
    digest = hashlib.sha256()
    for relative in source_files:
        path = formal_dir / relative
        if not path.is_file():
            raise AttestationError(f"audited source file is missing: {relative}")
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def validate_axiom_audit(
    payload: Mapping[str, Any],
    *,
    endpoint_theorems: tuple[str, ...],
    allowed_axioms: tuple[str, ...],
) -> None:
    if payload.get("format") != "cace.lean-theorem-metadata":
        raise AttestationError("kernel axiom audit has unexpected format")
    theorems = payload.get("theorems")
    if not isinstance(theorems, list):
        raise AttestationError("kernel axiom audit theorems must be an array")
    names: list[str] = []
    allowed = set(allowed_axioms)
    for item in theorems:
        if not isinstance(item, Mapping):
            raise AttestationError("kernel axiom audit theorem record must be an object")
        name = require_nonempty(item.get("name", ""), "kernel axiom theorem name")
        axioms = item.get("axioms")
        if not isinstance(axioms, list) or any(not isinstance(ax, str) for ax in axioms):
            raise AttestationError(f"{name}: axioms must be a string array")
        unexpected = sorted(set(axioms) - allowed)
        if unexpected:
            raise AttestationError(f"{name}: non-whitelisted axioms: {unexpected}")
        if "sorryAx" in axioms:
            raise AttestationError(f"{name}: sorryAx is forbidden")
        names.append(name)
    if len(names) != len(set(names)):
        raise AttestationError("kernel axiom audit contains duplicate theorem records")
    if set(names) != set(endpoint_theorems):
        raise AttestationError(
            "kernel axiom audit endpoint set differs from ProofContract; "
            f"missing={sorted(set(endpoint_theorems) - set(names))}, "
            f"extra={sorted(set(names) - set(endpoint_theorems))}"
        )
    if payload.get("theorem_count") != len(endpoint_theorems):
        raise AttestationError("kernel axiom audit theorem_count differs from ProofContract")


def validate_environment_metadata(
    payload: Mapping[str, Any],
    *,
    contract,
    git_commit: str,
    mathlib_commit: str,
    axiom_audit_sha256: str,
) -> None:
    expected = {
        "artifact_schema": "cace-lean-theorem-metadata-v3",
        "metadata_state": "LEAN_GENERATED",
        "claim_id": contract.claim_id,
        "proof_contract_id": contract.contract_id,
        "proof_contract_sha256": contract.contract_sha256,
        "git_commit": git_commit,
        "mathlib_commit": mathlib_commit,
        "kernel_axiom_audit_sha256": axiom_audit_sha256,
        "kernel_axiom_audit_theorem_count": len(contract.endpoint_theorems),
        "endpoint_count": len(contract.endpoint_theorems),
    }
    for field, value in expected.items():
        if payload.get(field) != value:
            raise AttestationError(
                f"Lean environment metadata {field} mismatch: expected {value!r}, got {payload.get(field)!r}"
            )
    endpoints = payload.get("endpoints")
    if not isinstance(endpoints, list):
        raise AttestationError("Lean environment metadata endpoints must be an array")
    names = [item.get("theorem") for item in endpoints if isinstance(item, Mapping)]
    if len(names) != len(endpoints) or set(names) != set(contract.endpoint_theorems):
        raise AttestationError("Lean environment metadata endpoint set differs from ProofContract")
    require_sha256(str(payload.get("identity_sha256", "")), "Lean metadata identity_sha256")


def build_attestation(
    *,
    contract,
    git_commit: str,
    lean_version: str,
    lean_toolchain: str,
    mathlib_commit: str,
    source_bundle_sha256: str,
    lake_manifest_sha256: str,
    kernel_axiom_audit_sha256: str,
    lean_environment_metadata_sha256: str,
    lean_environment_identity_sha256: str,
    qualification_system: str,
    qualification_run_id: str,
    workflow_run_id: int,
    workflow_run_attempt: int,
    runner_name: str,
    runner_arch: str,
) -> dict[str, Any]:
    git_commit = require_commit(git_commit)
    mathlib_commit = require_commit(mathlib_commit, "mathlib_commit")
    for field, value in (
        ("source_bundle_sha256", source_bundle_sha256),
        ("lake_manifest_sha256", lake_manifest_sha256),
        ("kernel_axiom_audit_sha256", kernel_axiom_audit_sha256),
        ("lean_environment_metadata_sha256", lean_environment_metadata_sha256),
        ("lean_environment_identity_sha256", lean_environment_identity_sha256),
    ):
        require_sha256(value, field)
    qualification_system = require_nonempty(qualification_system, "qualification_system")
    qualification_run_id = require_nonempty(qualification_run_id, "qualification_run_id")
    lean_version = require_nonempty(lean_version, "lean_version")
    lean_toolchain = require_nonempty(lean_toolchain, "lean_toolchain")
    runner_name = require_nonempty(runner_name, "runner_name")
    runner_arch = require_nonempty(runner_arch, "runner_arch")
    if workflow_run_id <= 0 or workflow_run_attempt <= 0:
        raise AttestationError("workflow run id and attempt must be positive")
    expected_toolchain = contract.dependency_pins.get("lean_toolchain")
    if not expected_toolchain:
        raise AttestationError("ProofContract is missing the Lean toolchain dependency pin")
    if lean_toolchain != expected_toolchain:
        raise AttestationError("attested Lean toolchain differs from ProofContract pin")
    if mathlib_commit != contract.dependency_pins.get("mathlib_commit"):
        raise AttestationError("attested Mathlib commit differs from ProofContract pin")

    checks = list(contract.required_checks)
    if len(checks) != len(set(checks)):
        raise AttestationError("ProofContract required checks contain duplicates")

    return {
        "attestation_schema": ATTESTATION_SCHEMA,
        "status": "PASS",
        "claim_id": contract.claim_id,
        "proof_contract_id": contract.contract_id,
        "proof_contract_sha256": contract.contract_sha256,
        "git_commit": git_commit,
        "formal_system": contract.formal_system,
        "build_target": contract.build_target,
        "lean_version": lean_version,
        "lean_toolchain": lean_toolchain,
        "mathlib_commit": mathlib_commit,
        "audited_source_files": list(contract.audited_source_files),
        "audited_source_bundle_sha256": source_bundle_sha256,
        "endpoint_theorems": list(contract.endpoint_theorems),
        "endpoint_count": len(contract.endpoint_theorems),
        "allowed_axioms": list(contract.allowed_axioms),
        "lake_manifest_sha256": lake_manifest_sha256,
        "kernel_axiom_audit_sha256": kernel_axiom_audit_sha256,
        "lean_environment_metadata_sha256": lean_environment_metadata_sha256,
        "lean_environment_identity_sha256": lean_environment_identity_sha256,
        "qualification_checks": checks,
        "qualification_system": qualification_system,
        "qualification_run_id": qualification_run_id,
        "workflow_run_id": workflow_run_id,
        "workflow_run_attempt": workflow_run_attempt,
        "runner_name": runner_name,
        "runner_arch": runner_arch,
        "current_head_required": True,
        "cache_policy": CACHE_POLICY,
        "nonclaims": list(contract.nonclaims),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--formal-dir", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--axiom-audit", type=Path, required=True)
    parser.add_argument("--git-commit", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workflow-run-id", type=int, default=None)
    parser.add_argument("--workflow-run-attempt", type=int, default=None)
    args = parser.parse_args(argv)

    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    from cace_studio.core.proof_contract import ProofContractRegistry

    contract = ProofContractRegistry.load_default().for_claim(CLAIM_ID)
    if contract is None:
        print("attestation rejected: canonical continuum ProofContract is missing", file=sys.stderr)
        return 2

    try:
        formal_dir = args.formal_dir.resolve()
        metadata_path = args.metadata.resolve()
        axiom_audit_path = args.axiom_audit.resolve()
        expected_commit = require_commit(args.git_commit, "--git-commit")
        repo_head = require_commit(command_output(["git", "rev-parse", "HEAD"], cwd=repo_root), "repository HEAD")
        if repo_head != expected_commit:
            raise AttestationError(
                f"repository HEAD {repo_head} differs from requested exact commit {expected_commit}"
            )
        if command_output(["git", "status", "--porcelain", "--untracked-files=no"], cwd=repo_root):
            raise AttestationError("repository tracked tree is not clean")

        mathlib_commit = require_commit(
            command_output(["git", "-C", str(formal_dir / ".lake/packages/mathlib"), "rev-parse", "HEAD"]),
            "mathlib_commit",
        )
        if mathlib_commit != contract.dependency_pins.get("mathlib_commit"):
            raise AttestationError("resolved Mathlib commit differs from ProofContract pin")

        manifest_path = formal_dir / "lake-manifest.json"
        if not manifest_path.is_file():
            raise AttestationError("resolved lake-manifest.json is missing")
        toolchain = (formal_dir / "lean-toolchain").read_text(encoding="utf-8").strip()
        lean_version = command_output(["lean", "--version"], cwd=formal_dir)

        axiom_payload = json.loads(axiom_audit_path.read_text(encoding="utf-8"))
        if not isinstance(axiom_payload, Mapping):
            raise AttestationError("kernel axiom audit must be a JSON object")
        validate_axiom_audit(
            axiom_payload,
            endpoint_theorems=contract.endpoint_theorems,
            allowed_axioms=contract.allowed_axioms,
        )
        axiom_sha = sha256_file(axiom_audit_path)

        metadata_payload = json.loads(metadata_path.read_text(encoding="utf-8"))
        if not isinstance(metadata_payload, Mapping):
            raise AttestationError("Lean environment metadata must be a JSON object")
        validate_environment_metadata(
            metadata_payload,
            contract=contract,
            git_commit=expected_commit,
            mathlib_commit=mathlib_commit,
            axiom_audit_sha256=axiom_sha,
        )

        workflow_run_id = args.workflow_run_id or int(os.environ.get("GITHUB_RUN_ID", "0"))
        workflow_run_attempt = args.workflow_run_attempt or int(os.environ.get("GITHUB_RUN_ATTEMPT", "0"))
        qualification_system = QUALIFICATION_SYSTEM if os.environ.get("GITHUB_ACTIONS") == "true" else "local-exact-head"
        qualification_run_id = str(workflow_run_id) if workflow_run_id > 0 else f"local:{expected_commit}"

        attestation = build_attestation(
            contract=contract,
            git_commit=expected_commit,
            lean_version=lean_version,
            lean_toolchain=toolchain,
            mathlib_commit=mathlib_commit,
            source_bundle_sha256=audited_source_bundle_sha256(formal_dir, contract.audited_source_files),
            lake_manifest_sha256=sha256_file(manifest_path),
            kernel_axiom_audit_sha256=axiom_sha,
            lean_environment_metadata_sha256=sha256_file(metadata_path),
            lean_environment_identity_sha256=str(metadata_payload["identity_sha256"]),
            qualification_system=qualification_system,
            qualification_run_id=qualification_run_id,
            workflow_run_id=workflow_run_id if workflow_run_id > 0 else 1,
            workflow_run_attempt=workflow_run_attempt if workflow_run_attempt > 0 else 1,
            runner_name=os.environ.get("RUNNER_NAME", "local"),
            runner_arch=os.environ.get("RUNNER_ARCH", os.uname().machine),
        )
    except (AttestationError, OSError, ValueError, json.JSONDecodeError, KeyError) as exc:
        print(f"attestation rejected: {exc}", file=sys.stderr)
        return 2

    args.output.parent.mkdir(parents=True, exist_ok=True)
    rendered = canonical_json_bytes(attestation)
    args.output.write_bytes(rendered)
    digest = sha256_bytes(rendered)
    args.output.with_suffix(args.output.suffix + ".sha256").write_text(
        f"{digest}  {args.output.name}\n", encoding="utf-8"
    )
    print(f"continuum qualification attestation PASS: {args.output}")
    print(f"proof_artifact_sha256: {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
