from __future__ import annotations

import copy

import pytest

from cace_studio.core.attestation import (
    AttestationError,
    AttestationStatement,
    attestation_from_payload,
    generate_ed25519_keypair_pem,
    public_key_id,
    sign_attestation,
    verify_attestation,
)


def _statement(key_id: str) -> AttestationStatement:
    return AttestationStatement(
        verifier_id="independent-lab-A",
        verifier_key_id=key_id,
        claim_id="cace.test.claim",
        bundle_sha256="a" * 64,
        created_at_utc="2026-09-15T01:02:03Z",
        purpose="independent-reproduction",
        bindings={"git_commit": "b" * 40},
    )


def test_ed25519_attestation_round_trip_and_key_binding():
    private_pem, public_pem = generate_ed25519_keypair_pem()
    key_id = public_key_id(public_pem)
    signed = sign_attestation(_statement(key_id), private_pem)

    assert verify_attestation(signed) == key_id
    restored = attestation_from_payload(signed.payload())
    assert verify_attestation(restored) == key_id
    assert restored.statement.bundle_sha256 == "a" * 64
    assert restored.proof_effect == "none"
    assert restored.statement.proof_effect == "none"


def test_statement_tamper_is_detected_before_signature_promotion():
    private_pem, public_pem = generate_ed25519_keypair_pem()
    signed = sign_attestation(_statement(public_key_id(public_pem)), private_pem)
    payload = copy.deepcopy(signed.payload())
    payload["statement"]["claim_id"] = "cace.test.other"

    with pytest.raises(AttestationError):
        attestation_from_payload(payload)


def test_signing_key_must_match_declared_verifier_key_id():
    private_a, public_a = generate_ed25519_keypair_pem()
    private_b, _ = generate_ed25519_keypair_pem()
    statement = _statement(public_key_id(public_a))

    with pytest.raises(AttestationError, match="does not match"):
        sign_attestation(statement, private_b)


def test_envelope_is_fail_closed_on_unknown_fields_and_proof_effect():
    private_pem, public_pem = generate_ed25519_keypair_pem()
    signed = sign_attestation(_statement(public_key_id(public_pem)), private_pem)

    extra = copy.deepcopy(signed.payload())
    extra["unexpected"] = True
    with pytest.raises(AttestationError, match="keys mismatch"):
        attestation_from_payload(extra)

    promoted = copy.deepcopy(signed.payload())
    promoted["proof_effect"] = "formal-promotion"
    with pytest.raises(AttestationError):
        attestation_from_payload(promoted)


def test_attestation_timestamp_and_purpose_are_canonical():
    _, public_pem = generate_ed25519_keypair_pem()
    key_id = public_key_id(public_pem)

    with pytest.raises(AttestationError):
        AttestationStatement(
            verifier_id="v",
            verifier_key_id=key_id,
            claim_id="claim",
            bundle_sha256="c" * 64,
            created_at_utc="2026-09-15T01:02:03.123Z",
        )

    with pytest.raises(AttestationError):
        AttestationStatement(
            verifier_id="v",
            verifier_key_id=key_id,
            claim_id="claim",
            bundle_sha256="c" * 64,
            created_at_utc="2026-09-15T01:02:03Z",
            purpose="proof-promotion",
        )
