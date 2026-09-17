from __future__ import annotations

import json

import pytest

from cace_studio.core.proof_contract import ProofContractRegistry
from scripts import promote_v330_qualification as promotion


def test_promotion_updates_claim_and_ledger_from_single_attestation_source():
    claims = json.loads(promotion.CLAIM_REGISTRY_PATH.read_text(encoding="utf-8"))
    ledger = json.loads(promotion.PROOF_LEDGER_PATH.read_text(encoding="utf-8"))
    contract = ProofContractRegistry.load_default().for_claim(promotion.CLAIM_ID)
    assert contract is not None
    attestation = {
        "git_commit": "a" * 40,
        "workflow_run_id": 12345,
    }
    digest = "b" * 64

    new_claims, new_ledger = promotion.promoted_payloads(
        claims,
        ledger,
        attestation=attestation,
        attestation_sha256=digest,
        contract=contract,
    )
    claim = next(item for item in new_claims["claims"] if item["claim_id"] == promotion.CLAIM_ID)
    entry = next(item for item in new_ledger["entries"] if promotion.CLAIM_ID in item["claim_ids"])

    assert claim["qualification"]["attested_commit"] == "a" * 40
    assert claim["qualification"]["proof_artifact_sha256"] == digest
    assert claim["qualification"]["status"] == "PASS"
    assert entry["commit"] == claim["qualification"]["attested_commit"]
    assert entry["proof_artifact_sha256"] == digest
    assert entry["proof_contract_sha256"] == contract.contract_sha256
    assert entry["checks"] == list(contract.required_checks)
    assert entry["workflow_run_id"] == 12345
    assert entry["qualification_run_id"] == "12345"
    assert entry["blockers"] == []


def test_evidence_validation_rejects_external_attestation_hash_mismatch(tmp_path):
    artifact = tmp_path / "artifact"
    artifact.mkdir()
    (artifact / promotion.ATTESTATION).write_text("{}\n", encoding="utf-8")
    (artifact / promotion.SOURCE_BINDING_REPORT).write_text("{}\n", encoding="utf-8")

    with pytest.raises(promotion.PromotionError, match="attestation SHA-256"):
        promotion.validate_evidence(
            artifact,
            expected_git_commit="a" * 40,
            expected_attestation_sha256="b" * 64,
            expected_workflow_run_id=1,
            expected_workflow_run_attempt=1,
        )


def test_apply_transaction_restores_both_files_on_second_replace_failure(tmp_path, monkeypatch):
    claims_path = tmp_path / "claim_registry.json"
    ledger_path = tmp_path / "proof_ledger.json"
    claims_path.write_text('{"old":"claims"}\n', encoding="utf-8")
    ledger_path.write_text('{"old":"ledger"}\n', encoding="utf-8")
    monkeypatch.setattr(promotion, "CLAIM_REGISTRY_PATH", claims_path)
    monkeypatch.setattr(promotion, "PROOF_LEDGER_PATH", ledger_path)

    original_replace = type(claims_path).replace
    calls = {"count": 0}

    def flaky_replace(self, target):
        calls["count"] += 1
        if calls["count"] == 2:
            raise OSError("simulated second-file replacement failure")
        return original_replace(self, target)

    monkeypatch.setattr(type(claims_path), "replace", flaky_replace)
    with pytest.raises(OSError, match="simulated"):
        promotion.apply_transaction({"new": "claims"}, {"new": "ledger"})

    assert claims_path.read_text(encoding="utf-8") == '{"old":"claims"}\n'
    assert ledger_path.read_text(encoding="utf-8") == '{"old":"ledger"}\n'
