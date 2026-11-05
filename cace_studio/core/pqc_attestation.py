"""Additive CACE ML-DSA-65 provenance attestation profile."""
from __future__ import annotations

import base64
import hashlib
from collections.abc import Mapping
from datetime import datetime
from typing import Any

from .reproducibility import canonical_json_bytes

SCHEMA = "cace-signed-attestation-v2"
STATEMENT_SCHEMA = "cace-attestation-statement-v2"
ALGORITHM = "ML-DSA-65"
CANONICALIZATION = "sha256/cace-canonical-json-v1"
DOMAIN = b"CACE:TITAN:SIGNED-ATTESTATION:v2\\0"
PROOF_EFFECT = "none"
STATEMENT_KEYS = {
    "schema", "signature_algorithm", "proof_effect", "verifier_id",
    "verifier_key_id", "claim_id", "bundle_sha256", "created_at_utc",
    "purpose", "bindings",
}
ENVELOPE_KEYS = {
    "schema", "signature_algorithm", "proof_effect", "canonicalization",
    "domain_separator", "statement_sha256", "statement", "public_key_b64",
    "signature_b64",
}


class PQCAttestationError(ValueError):
    """Invalid CACE ML-DSA provenance attestation."""


class PQCProviderUnavailable(RuntimeError):
    """Optional OQS provider is not installed or enabled."""


def _provider():
    try:
        import oqs
    except ImportError as exc:
        raise PQCProviderUnavailable("Install pinned liboqs-python 0.16.0.2") from exc
    return oqs


def _sha256(value: Any, name: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise PQCAttestationError(f"{name} must be lowercase SHA-256 hex")
    return value


def _utc(value: Any) -> str:
    if not isinstance(value, str):
        raise PQCAttestationError("created_at_utc must be a string")
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise PQCAttestationError("created_at_utc must be YYYY-MM-DDTHH:MM:SSZ") from exc
    if parsed.strftime("%Y-%m-%dT%H:%M:%SZ") != value:
        raise PQCAttestationError("created_at_utc is not canonical")
    return value


def _statement_bytes(statement: Mapping[str, Any]) -> bytes:
    if set(statement) != STATEMENT_KEYS:
        raise PQCAttestationError("statement keys mismatch")
    if statement["schema"] != STATEMENT_SCHEMA or statement["signature_algorithm"] != ALGORITHM:
        raise PQCAttestationError("unsupported ML-DSA statement schema or algorithm")
    if statement["proof_effect"] != PROOF_EFFECT:
        raise PQCAttestationError("attestation proof_effect must be none")
    if not isinstance(statement["verifier_id"], str) or not statement["verifier_id"].strip():
        raise PQCAttestationError("verifier_id must be non-empty")
    if not isinstance(statement["claim_id"], str) or not statement["claim_id"].strip():
        raise PQCAttestationError("claim_id must be non-empty")
    key_id = statement["verifier_key_id"]
    if not isinstance(key_id, str) or not key_id.startswith("ml-dsa-65:"):
        raise PQCAttestationError("verifier_key_id must use ml-dsa-65:<sha256>")
    _sha256(key_id.split(":", 1)[1], "verifier_key_id digest")
    _sha256(statement["bundle_sha256"], "bundle_sha256")
    _utc(statement["created_at_utc"])
    if statement["purpose"] not in {"artifact-integrity", "independent-reproduction"}:
        raise PQCAttestationError("unsupported attestation purpose")
    if not isinstance(statement["bindings"], Mapping):
        raise PQCAttestationError("bindings must be an object")
    return DOMAIN + canonical_json_bytes(dict(statement))


def public_key_id(public_key: bytes) -> str:
    if not isinstance(public_key, bytes) or not public_key:
        raise PQCAttestationError("public key must be non-empty bytes")
    return "ml-dsa-65:" + hashlib.sha256(public_key).hexdigest()


def sign_ml_dsa65(statement: Mapping[str, Any], secret_key: bytes, public_key: bytes) -> dict[str, Any]:
    """Sign canonical statement bytes using the vetted OQS binding."""
    if not isinstance(secret_key, bytes) or not secret_key:
        raise PQCAttestationError("secret key must be non-empty bytes")
    if statement.get("verifier_key_id") != public_key_id(public_key):
        raise PQCAttestationError("statement verifier_key_id does not match public key")
    message = _statement_bytes(statement)
    oqs = _provider()
    try:
        with oqs.Signature(ALGORITHM, secret_key=secret_key) as signer:
            signature = signer.sign(message)
    except Exception as exc:
        raise PQCAttestationError(f"ML-DSA signing failed: {type(exc).__name__}") from exc
    return {
        "schema": SCHEMA,
        "signature_algorithm": ALGORITHM,
        "proof_effect": PROOF_EFFECT,
        "canonicalization": CANONICALIZATION,
        "domain_separator": "CACE:TITAN:SIGNED-ATTESTATION:v2\\0",
        "statement_sha256": hashlib.sha256(message).hexdigest(),
        "statement": dict(statement),
        "public_key_b64": base64.b64encode(public_key).decode("ascii"),
        "signature_b64": base64.b64encode(signature).decode("ascii"),
    }


def verify_ml_dsa65(envelope: Mapping[str, Any], *, trusted_verifier_id: str | None = None) -> str:
    """Verify the signature and internal bindings; trust policy remains external."""
    if set(envelope) != ENVELOPE_KEYS:
        raise PQCAttestationError("envelope keys do not match v2 schema")
    if envelope["schema"] != SCHEMA or envelope["signature_algorithm"] != ALGORITHM:
        raise PQCAttestationError("unsupported envelope schema or signature algorithm")
    if envelope["proof_effect"] != PROOF_EFFECT or envelope["canonicalization"] != CANONICALIZATION:
        raise PQCAttestationError("unsupported proof effect or canonicalization")
    if envelope["domain_separator"] != "CACE:TITAN:SIGNED-ATTESTATION:v2\\0":
        raise PQCAttestationError("domain separator mismatch")
    statement = envelope["statement"]
    if not isinstance(statement, Mapping):
        raise PQCAttestationError("statement must be an object")
    if trusted_verifier_id is not None and statement.get("verifier_id") != trusted_verifier_id:
        raise PQCAttestationError("verifier identity is not trusted by supplied policy")
    message = _statement_bytes(statement)
    if envelope["statement_sha256"] != hashlib.sha256(message).hexdigest():
        raise PQCAttestationError("statement digest mismatch")
    try:
        public_key = base64.b64decode(envelope["public_key_b64"], validate=True)
        signature = base64.b64decode(envelope["signature_b64"], validate=True)
    except Exception as exc:
        raise PQCAttestationError("public key or signature is not valid base64") from exc
    if base64.b64encode(public_key).decode("ascii") != envelope["public_key_b64"]:
        raise PQCAttestationError("public key encoding is not canonical base64")
    if base64.b64encode(signature).decode("ascii") != envelope["signature_b64"]:
        raise PQCAttestationError("signature encoding is not canonical base64")
    if statement["verifier_key_id"] != public_key_id(public_key):
        raise PQCAttestationError("public key ID mismatch")
    oqs = _provider()
    try:
        with oqs.Signature(ALGORITHM) as verifier:
            valid = verifier.verify(message, signature, public_key)
    except Exception as exc:
        raise PQCAttestationError(f"ML-DSA verification failed: {type(exc).__name__}") from exc
    if not valid:
        raise PQCAttestationError("ML-DSA signature is invalid")
    return statement["verifier_key_id"]
