from __future__ import annotations

from cace_studio.core.attestation import (
    AttestationStatement,
    generate_ed25519_keypair_pem,
    public_key_id,
    sign_attestation,
)
from cace_studio.core.claim_registry import ClaimRegistry
from cace_studio.core.cross_verification import evaluate_e5
from cace_studio.core.proof_contract import ProofContractRegistry
from cace_studio.core.proof_ledger import ProofLedger


COMMIT = "a" * 40
PROOF_SHA = "b" * 64
BUNDLE_SHA = "c" * 64
CLAIM_ID = "claim.test"
CONTRACT_ID = "proof.test.v1"


def _contracts():
    return ProofContractRegistry.from_mapping(
        {
            "schema_version": 1,
            "policy": "fail-closed",
            "contracts": [
                {
                    "contract_id": CONTRACT_ID,
                    "claim_id": CLAIM_ID,
                    "formal_system": "lean4",
                    "build_target": "Test.Audit",
                    "toolchain_file": "formal/test/lean-toolchain",
                    "dependency_pins": {"mathlib_commit": "1" * 40},
                    "endpoint_theorems": ["Test.endpoint"],
                    "audited_source_files": ["Test/Audit.lean"],
                    "allowed_axioms": ["propext"],
                    "required_checks": ["pinned-build", "axiom-audit"],
                    "nonclaims": ["Not a broader theorem."],
                    "theorem_dependency_metadata": {
                        "state": "NOT_GENERATED",
                        "note": "No theorem dependency graph generated.",
                    },
                }
            ],
        }
    )


def _registry(qualified=True):
    return ClaimRegistry.from_mapping(
        {
            "schema_version": 1,
            "policy": "fail-closed",
            "claims": [
                {
                    "claim_id": CLAIM_ID,
                    "module_ids": ["m.test"],
                    "statement": "test theorem",
                    "scope": "test",
                    "evidence_ceiling": "cross-verified",
                    "proof_contract_id": CONTRACT_ID,
                    "qualification": {
                        "status": "PASS" if qualified else "NOT_RUN",
                        "current_head_qualified": qualified,
                        "attested_commit": COMMIT if qualified else None,
                        "proof_artifact_sha256": PROOF_SHA if qualified else None,
                        "reason": "" if qualified else "not qualified",
                    },
                    "nonclaims": [],
                }
            ],
        }
    )


def _ledger(contracts, qualified=True, *, contract_hash=None):
    contract = contracts.for_claim(CLAIM_ID)
    contract_hash = contract.contract_sha256 if contract_hash is None else contract_hash
    return ProofLedger.from_mapping(
        {
            "schema_version": 1,
            "policy": "fail-closed",
            "entries": [
                {
                    "release": "test",
                    "claim_ids": [CLAIM_ID],
                    "status": "PASS" if qualified else "NOT_RUN",
                    "current_head_qualified": qualified,
                    "commit": COMMIT if qualified else None,
                    "proof_artifact_sha256": PROOF_SHA if qualified else None,
                    "proof_contract_id": CONTRACT_ID,
                    "proof_contract_sha256": contract_hash,
                    "qualification_system": "portable-test" if qualified else None,
                    "qualification_run_id": "run-1" if qualified else None,
                    "workflow_run_id": None,
                    "checks": ["pinned-build", "axiom-audit"] if qualified else [],
                    "blockers": [] if qualified else ["not run"],
                }
            ],
        }
    )


def _signed(
    verifier_id,
    contract,
    *,
    commit=COMMIT,
    proof_sha=PROOF_SHA,
    contract_id=CONTRACT_ID,
    contract_hash=None,
):
    private_pem, public_pem = generate_ed25519_keypair_pem()
    key_id = public_key_id(public_pem)
    statement = AttestationStatement(
        verifier_id=verifier_id,
        verifier_key_id=key_id,
        claim_id=CLAIM_ID,
        bundle_sha256=BUNDLE_SHA,
        created_at_utc="2026-09-15T01:00:00Z",
        bindings={
            "qualified_commit": commit,
            "proof_artifact_sha256": proof_sha,
            "proof_contract_id": contract_id,
            "proof_contract_sha256": contract.contract_sha256 if contract_hash is None else contract_hash,
        },
    )
    return sign_attestation(statement, private_pem), key_id


def test_e5_requires_already_qualified_claim_contract_and_two_independent_verifiers():
    contracts = _contracts()
    contract = contracts.for_claim(CLAIM_ID)
    first, key1 = _signed("verifier-a", contract)
    second, key2 = _signed("verifier-b", contract)
    result = evaluate_e5(
        CLAIM_ID,
        BUNDLE_SHA,
        [first, second],
        {key1: "verifier-a", key2: "verifier-b"},
        registry=_registry(),
        ledger=_ledger(contracts),
        contracts=contracts,
    )
    assert result.eligible is True
    assert result.status == "E5-CROSS-VERIFIED"
    assert result.proof_effect == "none"
    assert result.proof_contract_id == CONTRACT_ID
    assert result.proof_contract_sha256 == contract.contract_sha256
    assert result.verifier_ids == ("verifier-a", "verifier-b")


def test_e5_cannot_create_qualification():
    contracts = _contracts()
    contract = contracts.for_claim(CLAIM_ID)
    first, key1 = _signed("verifier-a", contract)
    second, key2 = _signed("verifier-b", contract)
    result = evaluate_e5(
        CLAIM_ID,
        BUNDLE_SHA,
        [first, second],
        {key1: "verifier-a", key2: "verifier-b"},
        registry=_registry(False),
        ledger=_ledger(contracts, False),
        contracts=contracts,
    )
    assert result.eligible is False
    assert "canonical claim is not current-head PASS qualified" in result.reasons


def test_e5_requires_distinct_verifier_identities_not_just_multiple_keys():
    contracts = _contracts()
    contract = contracts.for_claim(CLAIM_ID)
    first, key1 = _signed("same-verifier", contract)
    second, key2 = _signed("same-verifier", contract)
    result = evaluate_e5(
        CLAIM_ID,
        BUNDLE_SHA,
        [first, second],
        {key1: "same-verifier", key2: "same-verifier"},
        registry=_registry(),
        ledger=_ledger(contracts),
        contracts=contracts,
    )
    assert result.eligible is False
    assert any("distinct approved verifier identities" in reason for reason in result.reasons)


def test_e5_rejects_unapproved_or_wrongly_bound_attestations():
    contracts = _contracts()
    contract = contracts.for_claim(CLAIM_ID)
    first, key1 = _signed("verifier-a", contract)
    second, _ = _signed("verifier-b", contract, commit="d" * 40)
    result = evaluate_e5(
        CLAIM_ID,
        BUNDLE_SHA,
        [first, second],
        {key1: "verifier-a"},
        registry=_registry(),
        ledger=_ledger(contracts),
        contracts=contracts,
    )
    assert result.eligible is False
    assert any("verifier key is not approved" in reason for reason in result.reasons)


def test_e5_rejects_contract_drift_even_when_old_signatures_are_valid():
    contracts = _contracts()
    contract = contracts.for_claim(CLAIM_ID)
    first, key1 = _signed("verifier-a", contract)
    second, key2 = _signed("verifier-b", contract)
    stale_ledger = _ledger(contracts, contract_hash="f" * 64)
    result = evaluate_e5(
        CLAIM_ID,
        BUNDLE_SHA,
        [first, second],
        {key1: "verifier-a", key2: "verifier-b"},
        registry=_registry(),
        ledger=stale_ledger,
        contracts=contracts,
    )
    assert result.eligible is False
    assert "proof ledger is bound to a stale/different proof-contract hash" in result.reasons


def test_e5_attestation_must_bind_current_contract_hash():
    contracts = _contracts()
    contract = contracts.for_claim(CLAIM_ID)
    first, key1 = _signed("verifier-a", contract, contract_hash="f" * 64)
    second, key2 = _signed("verifier-b", contract)
    result = evaluate_e5(
        CLAIM_ID,
        BUNDLE_SHA,
        [first, second],
        {key1: "verifier-a", key2: "verifier-b"},
        registry=_registry(),
        ledger=_ledger(contracts),
        contracts=contracts,
    )
    assert result.eligible is False
    assert any("current proof-contract hash" in reason for reason in result.reasons)
