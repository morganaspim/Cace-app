from __future__ import annotations

import base64
import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Mapping

from .reproducibility import canonical_json_bytes

ATTESTATION_STATEMENT_SCHEMA = "cace-attestation-statement-v1"
ATTESTATION_ENVELOPE_SCHEMA = "cace-signed-attestation-v1"
SIGNATURE_ALGORITHM = "ed25519"
PROOF_EFFECT = "none"
_ALLOWED_PURPOSES = frozenset({"artifact-integrity", "independent-reproduction"})
_HEX = frozenset("0123456789abcdef")
_DOMAIN_ATTESTATION = b"CACE:SIGNED-ATTESTATION:v1\0"


class AttestationError(ValueError):
    """Raised when a signed attestation fails closed validation."""


class AttestationUnavailableError(RuntimeError):
    """Raised when the optional vetted cryptography dependency is unavailable."""


def _crypto():
    try:
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric.ed25519 import (
            Ed25519PrivateKey,
            Ed25519PublicKey,
        )
    except ImportError as exc:  # pragma: no cover - dependency packaging path
        raise AttestationUnavailableError(
            "Ed25519 attestations require the optional 'attest' dependency: "
            "pip install 'cace-studio[attest]'"
        ) from exc
    return InvalidSignature, serialization, Ed25519PrivateKey, Ed25519PublicKey


def _require_nonempty(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AttestationError(f"{field_name} must be a non-empty string")
    return value


def _require_sha256(value: Any, field_name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(ch not in _HEX for ch in value)
    ):
        raise AttestationError(
            f"{field_name} must be a lowercase 64-character SHA-256 hex digest"
        )
    return value


def _require_key_id(value: Any) -> str:
    if not isinstance(value, str) or not value.startswith("ed25519:"):
        raise AttestationError("verifier_key_id must use ed25519:<sha256> format")
    _require_sha256(value.split(":", 1)[1], "verifier key digest")
    return value


def _require_utc_second(value: Any) -> str:
    _require_nonempty(value, "created_at_utc")
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise AttestationError(
            "created_at_utc must use second-resolution UTC form YYYY-MM-DDTHH:MM:SSZ"
        ) from exc
    if parsed.strftime("%Y-%m-%dT%H:%M:%SZ") != value:
        raise AttestationError("created_at_utc is not canonical UTC")
    return value


def _require_exact_keys(
    payload: Mapping[str, Any],
    expected: set[str],
    context: str,
) -> None:
    actual = set(payload)
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    if missing or extra:
        raise AttestationError(
            f"{context} keys mismatch; missing={missing}, extra={extra}"
        )


def _decode_signature(value: Any) -> bytes:
    if not isinstance(value, str):
        raise AttestationError("signature_b64 must be a string")
    try:
        decoded = base64.b64decode(value.encode("ascii"), validate=True)
    except Exception as exc:
        raise AttestationError("signature_b64 is not valid canonical base64") from exc
    if len(decoded) != 64:
        raise AttestationError("Ed25519 signatures must be exactly 64 bytes")
    if base64.b64encode(decoded).decode("ascii") != value:
        raise AttestationError("signature_b64 is not canonical base64")
    return decoded


@dataclass(frozen=True)
class AttestationStatement:
    verifier_id: str
    verifier_key_id: str
    claim_id: str
    bundle_sha256: str
    created_at_utc: str
    purpose: str = "independent-reproduction"
    bindings: Mapping[str, Any] = field(default_factory=dict)
    schema: str = ATTESTATION_STATEMENT_SCHEMA
    signature_algorithm: str = SIGNATURE_ALGORITHM
    proof_effect: str = PROOF_EFFECT

    def __post_init__(self) -> None:
        if self.schema != ATTESTATION_STATEMENT_SCHEMA:
            raise AttestationError(f"unsupported attestation statement schema: {self.schema!r}")
        if self.signature_algorithm != SIGNATURE_ALGORITHM:
            raise AttestationError(
                f"unsupported signature algorithm: {self.signature_algorithm!r}"
            )
        if self.proof_effect != PROOF_EFFECT:
            raise AttestationError(
                "signed attestations are provenance/cross-check metadata and must "
                "have proof_effect='none'"
            )
        _require_nonempty(self.verifier_id, "verifier_id")
        _require_key_id(self.verifier_key_id)
        _require_nonempty(self.claim_id, "claim_id")
        _require_sha256(self.bundle_sha256, "bundle_sha256")
        _require_utc_second(self.created_at_utc)
        if self.purpose not in _ALLOWED_PURPOSES:
            raise AttestationError(
                f"unsupported attestation purpose {self.purpose!r}; "
                f"allowed={sorted(_ALLOWED_PURPOSES)}"
            )
        if not isinstance(self.bindings, Mapping):
            raise AttestationError("attestation bindings must be an object")

    def payload(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "signature_algorithm": self.signature_algorithm,
            "proof_effect": self.proof_effect,
            "verifier_id": self.verifier_id,
            "verifier_key_id": self.verifier_key_id,
            "claim_id": self.claim_id,
            "bundle_sha256": self.bundle_sha256,
            "created_at_utc": self.created_at_utc,
            "purpose": self.purpose,
            "bindings": dict(self.bindings),
        }

    @property
    def signing_bytes(self) -> bytes:
        return _DOMAIN_ATTESTATION + canonical_json_bytes(self.payload())

    @property
    def statement_sha256(self) -> str:
        return hashlib.sha256(self.signing_bytes).hexdigest()


@dataclass(frozen=True)
class SignedAttestation:
    statement: AttestationStatement
    public_key_pem: str
    signature_b64: str
    statement_sha256: str
    schema: str = ATTESTATION_ENVELOPE_SCHEMA
    signature_algorithm: str = SIGNATURE_ALGORITHM
    proof_effect: str = PROOF_EFFECT

    def __post_init__(self) -> None:
        if self.schema != ATTESTATION_ENVELOPE_SCHEMA:
            raise AttestationError(f"unsupported signed attestation schema: {self.schema!r}")
        if self.signature_algorithm != SIGNATURE_ALGORITHM:
            raise AttestationError(
                f"unsupported signature algorithm: {self.signature_algorithm!r}"
            )
        if self.proof_effect != PROOF_EFFECT:
            raise AttestationError(
                "signed attestations cannot promote proofs and must have proof_effect='none'"
            )
        _require_nonempty(self.public_key_pem, "public_key_pem")
        _decode_signature(self.signature_b64)
        _require_sha256(self.statement_sha256, "statement_sha256")
        if self.statement_sha256 != self.statement.statement_sha256:
            raise AttestationError(
                "statement_sha256 does not match the canonical domain-separated statement"
            )

    def payload(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "signature_algorithm": self.signature_algorithm,
            "proof_effect": self.proof_effect,
            "statement_sha256": self.statement_sha256,
            "statement": self.statement.payload(),
            "public_key_pem": self.public_key_pem,
            "signature_b64": self.signature_b64,
        }


def generate_ed25519_keypair_pem() -> tuple[bytes, bytes]:
    """Generate a vetted Ed25519 keypair serialized as standard PEM."""
    _, serialization, Ed25519PrivateKey, _ = _crypto()
    private_key = Ed25519PrivateKey.generate()
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return private_pem, public_pem


def _load_public_key(public_key_pem: bytes):
    _, serialization, _, Ed25519PublicKey = _crypto()
    try:
        key = serialization.load_pem_public_key(public_key_pem)
    except (TypeError, ValueError) as exc:
        raise AttestationError("invalid public-key PEM") from exc
    if not isinstance(key, Ed25519PublicKey):
        raise AttestationError("attestation public key must be Ed25519")
    return key


def public_key_id(public_key_pem: bytes) -> str:
    _, serialization, _, _ = _crypto()
    key = _load_public_key(public_key_pem)
    raw = key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return "ed25519:" + hashlib.sha256(raw).hexdigest()


def sign_attestation(
    statement: AttestationStatement,
    private_key_pem: bytes,
) -> SignedAttestation:
    _, serialization, Ed25519PrivateKey, _ = _crypto()
    try:
        private_key = serialization.load_pem_private_key(
            private_key_pem,
            password=None,
        )
    except (TypeError, ValueError) as exc:
        raise AttestationError("invalid or encrypted private-key PEM") from exc
    if not isinstance(private_key, Ed25519PrivateKey):
        raise AttestationError("attestation private key must be Ed25519")
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    actual_key_id = public_key_id(public_pem)
    if statement.verifier_key_id != actual_key_id:
        raise AttestationError(
            "statement verifier_key_id does not match the signing private key"
        )
    signature = private_key.sign(statement.signing_bytes)
    return SignedAttestation(
        statement=statement,
        public_key_pem=public_pem.decode("ascii"),
        signature_b64=base64.b64encode(signature).decode("ascii"),
        statement_sha256=statement.statement_sha256,
    )


def verify_attestation(attestation: SignedAttestation) -> str:
    InvalidSignature, _, _, _ = _crypto()
    attestation.__post_init__()
    public_pem = attestation.public_key_pem.encode("ascii")
    key = _load_public_key(public_pem)
    actual_key_id = public_key_id(public_pem)
    if attestation.statement.verifier_key_id != actual_key_id:
        raise AttestationError(
            "attestation verifier_key_id does not match the embedded public key"
        )
    signature = _decode_signature(attestation.signature_b64)
    try:
        key.verify(signature, attestation.statement.signing_bytes)
    except InvalidSignature as exc:
        raise AttestationError("Ed25519 signature verification failed") from exc
    return actual_key_id


def statement_from_payload(payload: Mapping[str, Any]) -> AttestationStatement:
    if not isinstance(payload, Mapping):
        raise AttestationError("attestation statement must be an object")
    _require_exact_keys(
        payload,
        {
            "schema",
            "signature_algorithm",
            "proof_effect",
            "verifier_id",
            "verifier_key_id",
            "claim_id",
            "bundle_sha256",
            "created_at_utc",
            "purpose",
            "bindings",
        },
        "attestation statement",
    )
    bindings = payload["bindings"]
    if not isinstance(bindings, Mapping):
        raise AttestationError("attestation bindings must be an object")
    return AttestationStatement(
        verifier_id=payload["verifier_id"],
        verifier_key_id=payload["verifier_key_id"],
        claim_id=payload["claim_id"],
        bundle_sha256=payload["bundle_sha256"],
        created_at_utc=payload["created_at_utc"],
        purpose=payload["purpose"],
        bindings=dict(bindings),
        schema=payload["schema"],
        signature_algorithm=payload["signature_algorithm"],
        proof_effect=payload["proof_effect"],
    )


def attestation_from_payload(payload: Mapping[str, Any]) -> SignedAttestation:
    if not isinstance(payload, Mapping):
        raise AttestationError("signed attestation must be an object")
    _require_exact_keys(
        payload,
        {
            "schema",
            "signature_algorithm",
            "proof_effect",
            "statement_sha256",
            "statement",
            "public_key_pem",
            "signature_b64",
        },
        "signed attestation",
    )
    statement = statement_from_payload(payload["statement"])
    result = SignedAttestation(
        statement=statement,
        public_key_pem=payload["public_key_pem"],
        signature_b64=payload["signature_b64"],
        statement_sha256=payload["statement_sha256"],
        schema=payload["schema"],
        signature_algorithm=payload["signature_algorithm"],
        proof_effect=payload["proof_effect"],
    )
    verify_attestation(result)
    return result
