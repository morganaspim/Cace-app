from __future__ import annotations

from cace_studio.core.attestation import (
    AttestationStatement,
    generate_ed25519_keypair_pem,
    public_key_id,
    sign_attestation,
)
from cace_studio.core.claim_registry import ClaimRegistry
from cace_studio.core.cross_verification import evaluate_e5
from cace_studio.core.proof_ledger import ProofLedger


COMMIT = "a" * 40
PROOF_SHA = "b" * 64
BUNDLE_SHA = "c" * 64
CLAIM_ID = "claim.test"


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


def _ledger(qualified=True):
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
                    "workflow_run_id": 123 if qualified else None,
                    "checks": ["kernel axiom audit"] if qualified else [],
                    "blockers": [] if qualified else ["not run"],
                }
            ],
        }
    )


def _signed(verifier_id, *, commit=COMMIT, proof_sha=PROOF_SHA):
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
        },
    )
    return sign_attestation(statement, private_pem), key_id


def test_e5_requires_already_qualified_claim_and_two_independent_approved_verifiers():
    first, key1 = _signed("verifier-a")
    second, key2 = _signed("verifier-b")
    result = evaluate_e5(
        CLAIM_ID,
        BUNDLE_SHA,
        [first, second],
        {key1: "verifier-a", key2: "verifier-b"},
        registry=_registry(),
        ledger=_ledger(),
    )
    assert result.eligible is True
    assert result.status == "E5-CROSS-VERIFIED"
    assert result.proof_effect == "none"
    assert result.verifier_ids == ("verifier-a", "verifier-b")


def test_e5_cannot_create_qualification():
    first, key1 = _signed("verifier-a")
    second, key2 = _signed("verifier-b")
    result = evaluate_e5(
        CLAIM_ID,
        BUNDLE_SHA,
        [first, second],
        {key1: "verifier-a", key2: "verifier-b"},
        registry=_registry(False),
        ledger=_ledger(False),
    )
    assert result.eligible is False
    assert "canonical claim is not current-head PASS qualified" in result.reasons


def test_e5_requires_distinct_verifier_identities_not_just_multiple_keys():
    first, key1 = _signed("same-verifier")
    second, key2 = _signed("same-verifier")
    result = evaluate_e5(
        CLAIM_ID,
        BUNDLE_SHA,
        [first, second],
        {key1: "same-verifier", key2: "same-verifier"},
        registry=_registry(),
        ledger=_ledger(),
    )
    assert result.eligible is False
    assert any("distinct approved verifier identities" in reason for reason in result.reasons)


def test_e5_rejects_unapproved_or_wrongly_bound_attestations():
    first, key1 = _signed("verifier-a")
    second, _ = _signed("verifier-b", commit="d" * 40)
    result = evaluate_e5(
        CLAIM_ID,
        BUNDLE_SHA,
        [first, second],
        {key1: "verifier-a"},
        registry=_registry(),
        ledger=_ledger(),
    )
    assert result.eligible is False
    assert any("verifier key is not approved" in reason for reason in result.reasons)
