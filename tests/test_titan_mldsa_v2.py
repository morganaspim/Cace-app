from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from cace_studio.core.evidence_ledger import EvidenceArtifact, EvidenceBundle
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
    # liboqs-python 0.16.0.2 must reject malformed key lengths before native calls.
    with oqs.Signature("ML-DSA-65") as verifier:
        with pytest.raises(ValueError):
            verifier.verify(b"message", b"bad", public_key[:8])

def test_cace_pqc_cli_keygen_sign_verify(tmp_path: Path) -> None:
    private_key = tmp_path / "verifier.sk"
    public_key = tmp_path / "verifier.pk"
    keygen = subprocess.run(
        [sys.executable, "-m", "cace_studio.attest_cli", "pqc-keygen",
         "--private-key", str(private_key), "--public-key", str(public_key)],
        capture_output=True, text=True, check=False,
    )
    assert keygen.returncode == 0, keygen.stderr
    assert private_key.exists() and public_key.exists()
    assert private_key.stat().st_mode & 0o077 == 0

    artifact_bytes = b"titan CLI evidence fixture"
    artifact_root = tmp_path / "artifact-root"
    artifact_root.mkdir()
    (artifact_root / "fixture.bin").write_bytes(artifact_bytes)
    artifact = EvidenceArtifact.from_bytes(
        "titan-fixture", artifact_bytes, role="execution-manifest",
        media_type="application/octet-stream", path="fixture.bin",
    )
    bundle = EvidenceBundle(artifacts=(artifact,), bindings={"fixture": True})
    bundle_doc = {
        "cli_schema": 1, "command": "titan-bundle", "proof_effect": "none",
        "bundle_sha256": bundle.bundle_sha256, "bundle": bundle.payload(),
    }
    bundle_path = tmp_path / "bundle.json"
    bundle_path.write_text(json.dumps(bundle_doc), encoding="utf-8")
    bindings_path = tmp_path / "bindings.json"
    bindings_path.write_text(json.dumps({
        "source_repository": "Mannyspiro/expert-robot",
        "source_commit_sha": "a" * 40,
        "workflow_run_id": 42,
        "provider_commit": "b" * 40,
        "vector_source_commit": "c" * 40,
        "verification_scope": "CLI smoke test only",
    }), encoding="utf-8")
    attestation_path = tmp_path / "attestation.json"
    signed = subprocess.run(
        [sys.executable, "-m", "cace_studio.attest_cli", "pqc-sign",
         "--bundle", str(bundle_path), "--artifact-root", str(artifact_root),
         "--private-key", str(private_key), "--public-key", str(public_key),
         "--bindings", str(bindings_path),
         "--verifier-id", "cace-titan-cli-test", "--claim-id", "titan:cli:test",
         "--output", str(attestation_path)],
        capture_output=True, text=True, check=False,
    )
    assert signed.returncode == 0, signed.stderr
    verified = subprocess.run(
        [sys.executable, "-m", "cace_studio.attest_cli", "pqc-verify",
         str(attestation_path), "--trusted-verifier-id", "cace-titan-cli-test"],
        capture_output=True, text=True, check=False,
    )
    assert verified.returncode == 0, verified.stderr
    assert json.loads(verified.stdout)["valid"] is True

def test_mldsa65_rejects_mismatched_keypair() -> None:
    with oqs.Signature("ML-DSA-65") as first:
        public_a = first.generate_keypair()
    with oqs.Signature("ML-DSA-65") as second:
        second.generate_keypair()
        secret_b = second.export_secret_key()
    with pytest.raises(PQCAttestationError):
        sign_ml_dsa65(statement_for(public_a), secret_b, public_a)
