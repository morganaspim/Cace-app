#!/usr/bin/env python3
"""Promote a verified v3.30 exact-head qualification into canonical provenance.

Dry-run is the default. Promotion requires externally supplied commit, attestation
SHA-256, workflow run id, and workflow attempt. The source-binding verification
report must agree with those anchors and with the current proof contract. Both the
claim registry and proof ledger are validated in memory before either file is changed;
apply mode restores both originals if either write or post-write validation fails.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
CLAIM_ID = "cace.v330.continuum-proof-strengthening"
ATTESTATION = "cace_continuum_qualification_attestation.json"
SOURCE_BINDING_REPORT = "v330_source_binding_verification.json"
CLAIM_REGISTRY_PATH = ROOT / "cace_studio/data/claim_registry.json"
PROOF_LEDGER_PATH = ROOT / "cace_studio/data/proof_ledger.json"
PROOF_CONTRACTS_PATH = ROOT / "cace_studio/data/proof_contracts.json"


class PromotionError(RuntimeError):
    pass


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _hex(value: Any, length: int, field: str) -> str:
    if not isinstance(value, str):
        raise PromotionError(f"{field} must be a string")
    value = value.strip().lower()
    if len(value) != length or any(c not in "0123456789abcdef" for c in value):
        raise PromotionError(f"{field} must be lowercase {length}-hex")
    return value


def _positive_int(value: Any, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise PromotionError(f"{field} must be a positive integer")
    return value


def _load(path: Path, field: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PromotionError(f"cannot load {field}: {exc}") from exc
    if not isinstance(value, dict):
        raise PromotionError(f"{field} must be a JSON object")
    return value


def _render(value: Mapping[str, Any]) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def _current_contract() -> tuple[Any, str]:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from cace_studio.core.proof_contract import ProofContractRegistry

    contract = ProofContractRegistry.load_default().for_claim(CLAIM_ID)
    if contract is None:
        raise PromotionError("canonical v3.30 proof contract is missing")
    return contract, contract.contract_sha256


def validate_evidence(
    artifact_dir: Path,
    *,
    expected_git_commit: str,
    expected_attestation_sha256: str,
    expected_workflow_run_id: int,
    expected_workflow_run_attempt: int,
) -> tuple[dict[str, Any], dict[str, Any], Any]:
    commit = _hex(expected_git_commit, 40, "expected_git_commit")
    digest = _hex(expected_attestation_sha256, 64, "expected_attestation_sha256")
    run_id = _positive_int(expected_workflow_run_id, "expected_workflow_run_id")
    attempt = _positive_int(expected_workflow_run_attempt, "expected_workflow_run_attempt")

    att_path = artifact_dir / ATTESTATION
    report_path = artifact_dir / SOURCE_BINDING_REPORT
    if not att_path.is_file() or not report_path.is_file():
        raise PromotionError("qualification artifact directory is missing attestation or source-binding report")
    att_bytes = att_path.read_bytes()
    if _sha(att_bytes) != digest:
        raise PromotionError("attestation SHA-256 differs from external trust anchor")
    att = _load(att_path, "qualification attestation")
    report = _load(report_path, "source-binding verification report")
    contract, contract_sha = _current_contract()

    expected = {
        "claim_id": CLAIM_ID,
        "git_commit": commit,
        "workflow_run_id": run_id,
        "workflow_run_attempt": attempt,
        "proof_contract_id": contract.contract_id,
        "proof_contract_sha256": contract_sha,
    }
    if att.get("status") != "PASS":
        raise PromotionError("qualification attestation status must be PASS")
    if report.get("status") != "PASS":
        raise PromotionError("source-binding verification status must be PASS")
    for field, value in expected.items():
        if att.get(field) != value:
            raise PromotionError(f"attestation {field} mismatch")
        if report.get(field) != value:
            raise PromotionError(f"source-binding report {field} mismatch")
    if report.get("attestation_sha256") != digest:
        raise PromotionError("source-binding report attestation SHA-256 mismatch")
    if att.get("qualification_system") != "github-actions":
        raise PromotionError("canonical promotion requires github-actions qualification")
    if str(att.get("qualification_run_id")) != str(run_id):
        raise PromotionError("qualification_run_id/workflow_run_id mismatch")
    if tuple(att.get("qualification_checks", ())) != contract.required_checks:
        raise PromotionError("attestation required-check set differs from current proof contract")
    return att, report, contract


def promoted_payloads(
    claims_raw: dict[str, Any],
    ledger_raw: dict[str, Any],
    *,
    attestation: Mapping[str, Any],
    attestation_sha256: str,
    contract,
) -> tuple[dict[str, Any], dict[str, Any]]:
    claims = json.loads(json.dumps(claims_raw))
    ledger = json.loads(json.dumps(ledger_raw))
    matches = [item for item in claims.get("claims", []) if item.get("claim_id") == CLAIM_ID]
    entries = [item for item in ledger.get("entries", []) if CLAIM_ID in item.get("claim_ids", [])]
    if len(matches) != 1 or len(entries) != 1:
        raise PromotionError("expected exactly one canonical claim and proof-ledger entry")
    claim = matches[0]
    entry = entries[0]
    commit = attestation["git_commit"]
    run_id = int(attestation["workflow_run_id"])
    checks = list(contract.required_checks)
    reason = (
        f"Canonical exact-head qualification run {run_id} passed at {commit}; "
        "the content-addressed qualification attestation is the proof artifact and "
        "independent source-bound verification passed."
    )
    claim["proof_contract_id"] = contract.contract_id
    claim["qualification"] = {
        "attested_commit": commit,
        "current_head_qualified": True,
        "proof_artifact_sha256": attestation_sha256,
        "reason": reason,
        "status": "PASS",
    }
    entry.update(
        {
            "blockers": [],
            "checks": checks,
            "commit": commit,
            "current_head_qualified": True,
            "proof_artifact_sha256": attestation_sha256,
            "proof_contract_id": contract.contract_id,
            "proof_contract_sha256": contract.contract_sha256,
            "qualification_run_id": str(run_id),
            "qualification_system": "github-actions",
            "status": "PASS",
            "workflow_run_id": run_id,
        }
    )

    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from cace_studio.core.claim_registry import ClaimRegistry
    from cace_studio.core.proof_ledger import ProofLedger

    ClaimRegistry.from_mapping(claims)
    ProofLedger.from_mapping(ledger)
    return claims, ledger


def _git_clean_exact(expected_commit: str) -> None:
    try:
        head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        dirty = subprocess.check_output(
            ["git", "status", "--porcelain", "--untracked-files=no"], cwd=ROOT, text=True
        ).strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise PromotionError(f"cannot establish repository state: {exc}") from exc
    if head != expected_commit:
        raise PromotionError(f"repository HEAD {head} differs from attested commit {expected_commit}")
    if dirty:
        raise PromotionError("tracked repository tree must be clean before promotion")


def apply_transaction(claims: Mapping[str, Any], ledger: Mapping[str, Any]) -> None:
    old_claims = CLAIM_REGISTRY_PATH.read_bytes()
    old_ledger = PROOF_LEDGER_PATH.read_bytes()
    claim_tmp = CLAIM_REGISTRY_PATH.with_suffix(".json.promote.tmp")
    ledger_tmp = PROOF_LEDGER_PATH.with_suffix(".json.promote.tmp")
    claim_tmp.write_bytes(_render(claims))
    ledger_tmp.write_bytes(_render(ledger))
    try:
        claim_tmp.replace(CLAIM_REGISTRY_PATH)
        ledger_tmp.replace(PROOF_LEDGER_PATH)
        _load(CLAIM_REGISTRY_PATH, "promoted claim registry")
        _load(PROOF_LEDGER_PATH, "promoted proof ledger")
    except Exception:
        CLAIM_REGISTRY_PATH.write_bytes(old_claims)
        PROOF_LEDGER_PATH.write_bytes(old_ledger)
        raise
    finally:
        claim_tmp.unlink(missing_ok=True)
        ledger_tmp.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument("--expected-git-commit", required=True)
    parser.add_argument("--expected-attestation-sha256", required=True)
    parser.add_argument("--expected-workflow-run-id", type=int, required=True)
    parser.add_argument("--expected-workflow-run-attempt", type=int, required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    try:
        att, report, contract = validate_evidence(
            args.artifact_dir,
            expected_git_commit=args.expected_git_commit,
            expected_attestation_sha256=args.expected_attestation_sha256,
            expected_workflow_run_id=args.expected_workflow_run_id,
            expected_workflow_run_attempt=args.expected_workflow_run_attempt,
        )
        claims, ledger = promoted_payloads(
            _load(CLAIM_REGISTRY_PATH, "claim registry"),
            _load(PROOF_LEDGER_PATH, "proof ledger"),
            attestation=att,
            attestation_sha256=args.expected_attestation_sha256,
            contract=contract,
        )
        result = {
            "schema": "cace-v330-qualification-promotion-plan-v1",
            "status": "VALIDATED",
            "apply": bool(args.apply),
            "claim_id": CLAIM_ID,
            "git_commit": att["git_commit"],
            "workflow_run_id": att["workflow_run_id"],
            "workflow_run_attempt": att["workflow_run_attempt"],
            "proof_contract_sha256": contract.contract_sha256,
            "proof_artifact_sha256": args.expected_attestation_sha256,
            "source_binding_status": report["status"],
        }
        if args.apply:
            _git_clean_exact(att["git_commit"])
            apply_transaction(claims, ledger)
            result["status"] = "APPLIED"
    except (PromotionError, OSError, ValueError, KeyError) as exc:
        print(f"qualification promotion rejected: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
