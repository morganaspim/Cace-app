#!/usr/bin/env python3
"""Build exact-current-head qualification evidence for the RMK Lean bridge."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

from cace_studio.core.lean_theorem_metadata import (
    LeanTheoremMetadataError,
    build_theorem_metadata,
    canonical_json_bytes,
    run_lean_axiom_audit,
)
from cace_studio.core.proof_contract import ProofContractRegistry


CLAIM_ID = "cace.rmk.runtime-formal-linkage-v1"
ARTIFACT_SCHEMA = "cace-rmk-formal-qualification-v1"
AUDIT_SOURCE = Path("CACEFormal/RMKAxiomAudit.lean")


class RMKQualificationError(RuntimeError):
    """Fail-closed RMK qualification error."""


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            separators=(",", ": "),
        )
        + "\n"
    ).encode("utf-8")


def _command_output(command: list[str], *, cwd: Path | None = None) -> str:
    try:
        return subprocess.check_output(
            command,
            cwd=cwd,
            text=True,
            stderr=subprocess.STDOUT,
        ).strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise RMKQualificationError(
            f"failed command {command!r}: {exc}"
        ) from exc


def _require_git_sha(value: str, field: str) -> str:
    value = value.strip().lower()
    if len(value) != 40 or any(ch not in "0123456789abcdef" for ch in value):
        raise RMKQualificationError(f"{field} must be a 40-hex Git SHA")
    return value


def _source_manifest(formal_dir: Path, source_files: tuple[str, ...]) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    for relative in sorted(source_files):
        path = (formal_dir / relative).resolve()
        try:
            path.relative_to(formal_dir)
        except ValueError as exc:
            raise RMKQualificationError(f"audited source escapes formal root: {relative}") from exc
        if not path.is_file():
            raise RMKQualificationError(f"missing audited source: {relative}")
        data = path.read_bytes()
        entries.append(
            {
                "path": relative,
                "sha256": _sha256_bytes(data),
                "size": len(data),
            }
        )
    payload = {
        "algorithm": "cace-rmk-audited-source-bundle-v1",
        "files": entries,
    }
    return {
        **payload,
        "bundle_sha256": _sha256_bytes(_canonical_bytes(payload)),
    }


def build_qualification(
    *,
    repo_root: Path,
    formal_dir: Path,
    expected_commit: str,
) -> tuple[dict[str, Any], dict[str, Any], str]:
    registry = ProofContractRegistry.load_default()
    contract = registry.for_claim(CLAIM_ID)
    if contract is None:
        raise RMKQualificationError(f"missing proof contract for {CLAIM_ID}")

    actual_head = _require_git_sha(
        _command_output(["git", "rev-parse", "HEAD"], cwd=repo_root),
        "repository HEAD",
    )
    expected_commit = _require_git_sha(expected_commit, "expected commit")
    if actual_head != expected_commit:
        raise RMKQualificationError(
            f"exact-head mismatch: actual {actual_head} != expected {expected_commit}"
        )

    toolchain = (formal_dir / "lean-toolchain").read_text(encoding="utf-8").strip()
    expected_toolchain = contract.dependency_pins.get("lean_toolchain")
    if toolchain != expected_toolchain:
        raise RMKQualificationError(
            f"Lean toolchain mismatch: expected {expected_toolchain}, got {toolchain}"
        )

    mathlib_commit = _require_git_sha(
        _command_output(
            ["git", "-C", str(formal_dir / ".lake/packages/mathlib"), "rev-parse", "HEAD"]
        ),
        "Mathlib commit",
    )
    expected_mathlib = contract.dependency_pins.get("mathlib_commit")
    if mathlib_commit != expected_mathlib:
        raise RMKQualificationError(
            f"Mathlib commit mismatch: expected {expected_mathlib}, got {mathlib_commit}"
        )

    audit_path = formal_dir / AUDIT_SOURCE
    audit_source = audit_path.read_text(encoding="utf-8")
    raw_output = run_lean_axiom_audit(
        formal_dir=formal_dir,
        audit_source_path=AUDIT_SOURCE,
    )
    audit = build_theorem_metadata(
        audit_source=audit_source,
        lean_output=raw_output,
        audit_source_label=AUDIT_SOURCE.as_posix(),
        allowed_axioms=contract.allowed_axioms,
    )

    actual_theorems = {str(item["name"]) for item in audit["theorems"]}
    expected_theorems = set(contract.endpoint_theorems)
    if actual_theorems != expected_theorems:
        raise RMKQualificationError(
            "RMK kernel audit theorem set differs from proof contract; "
            f"missing={sorted(expected_theorems - actual_theorems)}, "
            f"extra={sorted(actual_theorems - expected_theorems)}"
        )

    source_manifest = _source_manifest(formal_dir, contract.audited_source_files)
    lean_version = _command_output(["lean", "--version"])

    identity = {
        "artifact_schema": ARTIFACT_SCHEMA,
        "qualification_state": "LEAN_KERNEL_AUDITED",
        "claim_id": contract.claim_id,
        "proof_contract_id": contract.contract_id,
        "proof_contract_sha256": contract.contract_sha256,
        "git_commit": actual_head,
        "lean_version": lean_version,
        "lean_toolchain": toolchain,
        "mathlib_commit": mathlib_commit,
        "build_target": contract.build_target,
        "audited_source_bundle": source_manifest,
        "kernel_axiom_audit": audit,
        "theorem_count": len(contract.endpoint_theorems),
        "nonclaim": (
            "This artifact qualifies the exact Lean RMK bridge theorem surface only; "
            "runtime C++ source identity and algorithms outside the contract remain separate obligations."
        ),
    }
    artifact = {
        **identity,
        "identity_sha256": _sha256_bytes(_canonical_bytes(identity)),
    }
    return artifact, audit, raw_output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--formal-dir", type=Path, default=Path("formal/cace_formal"))
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--git-commit", required=True)
    args = parser.parse_args(argv)

    repo_root = Path(__file__).resolve().parents[1]
    formal_dir = args.formal_dir.resolve()
    output_dir = args.output_dir.resolve()

    try:
        artifact, audit, raw_output = build_qualification(
            repo_root=repo_root,
            formal_dir=formal_dir,
            expected_commit=args.git_commit,
        )
    except (RMKQualificationError, LeanTheoremMetadataError, OSError, ValueError) as exc:
        print(f"RMK formal qualification rejected: {exc}", file=sys.stderr)
        return 2

    output_dir.mkdir(parents=True, exist_ok=True)

    audit_path = output_dir / "rmk_kernel_axiom_audit.json"
    audit_payload = canonical_json_bytes(audit)
    audit_path.write_bytes(audit_payload)
    audit_digest = _sha256_bytes(audit_payload)
    (output_dir / "rmk_kernel_axiom_audit.json.sha256").write_text(
        f"{audit_digest}  {audit_path.name}\n",
        encoding="utf-8",
    )
    (output_dir / "rmk_kernel_axiom_audit.raw.txt").write_text(
        raw_output,
        encoding="utf-8",
    )

    artifact_path = output_dir / "rmk_formal_qualification.json"
    artifact_payload = _canonical_bytes(artifact)
    artifact_path.write_bytes(artifact_payload)
    artifact_digest = _sha256_bytes(artifact_payload)
    (output_dir / "rmk_formal_qualification.json.sha256").write_text(
        f"{artifact_digest}  {artifact_path.name}\n",
        encoding="utf-8",
    )

    print(f"CACE_RMK_FORMAL_QUALIFICATION_PASS theorem_count={artifact['theorem_count']}")
    print(f"identity_sha256={artifact['identity_sha256']}")
    print(f"artifact_sha256={artifact_digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
