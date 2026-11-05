from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import base64

import pytest
oqs = pytest.importorskip("oqs")

from cace_studio.core.pqc_attestation import (
    PQCAttestationError,
    public_key_id,
    sign_ml_dsa65,
    verify_ml_dsa65,
)


def statement_for(public_key: bytes) -> dict:
    return {
        "schema": "cace-attestation-statement-v2",
        "signature_algorithm": "ML-DSA-65",
        "proof_effect": "none",
        "verifier_id": "cace-titan-smoke-verifier",
        "verifier_key_id": public_key_id(public_key),
        "claim_id": "titan:test:receipt-v2",
        "bundle_sha256": hashlib.sha256(b"test evidence bundle").hexdigest(),
        "created_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "purpose": "independent-reproduction",
        "bindings": {
            "source_repository": "Mannyspiro/expert-robot",
            "source_commit_sha": "a" * 40,
            "workflow_run_id": 1,
            "provider_commit": "b" * 40,
            "vector_source_commit": "c" * 40,
            "verification_scope": "signature roundtrip smoke test only",
        },
    }


def test_mldsa65_sign_verify_and_tamper_rejection() -> None:
    with oqs.Signature("ML-DSA-65") as keygen:
        public_key = keygen.generate_keypair()
        secret_key = keygen.export_secret_key()
    envelope = sign_ml_dsa65(statement_for(public_key), secret_key, public_key)
    assert verify_ml_dsa65(envelope, trusted_verifier_id="cace-titan-smoke-verifier") == public_key_id(public_key)
    changed = dict(envelope)
    changed["statement"] = dict(envelope["statement"])
    changed["statement"]["claim_id"] = "titan:test:tampered"
    with pytest.raises(PQCAttestationError):
        verify_ml_dsa65(changed)


def test_mldsa65_rejects_short_public_key() -> None:
    with oqs.Signature("ML-DSA-65") as keygen:
        public_key = keygen.generate_keypair()
        secret_key = keygen.export_secret_key()
    envelope = sign_ml_dsa65(statement_for(public_key), secret_key, public_key)
    envelope["public_key_b64"] = base64.b64encode(public_key[:8]).decode("ascii")
    with pytest.raises(PQCAttestationError):
        verify_ml_dsa65(envelope)
