"""Independent verification adapter for Merlin RSI evidence bundles.

This module delegates bundle and signature semantics to CACE's own core
implementation. It does not create attestations, run candidate code, or grant
proof/promotion authority.
"""
from __future__ import annotations

import base64
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _approved_keys(trust_store_json: str, trust_store_sha256: str) -> dict[str, str]:
    if not trust_store_json or not re.fullmatch(r"[0-9a-f]{64}", trust_store_sha256 or ""):
        raise PermissionError("CACE Merlin RSI trust store is not configured")
    if _sha256(trust_store_json.encode("utf-8")) != trust_store_sha256:
        raise PermissionError("CACE Merlin RSI trust store digest mismatch")
    try:
        document = json.loads(trust_store_json)
    except (TypeError, ValueError) as exc:
        raise PermissionError("CACE Merlin RSI trust store is invalid JSON") from exc
    if (
        not isinstance(document, Mapping)
        or set(document) != {"schema", "keys"}
        or document.get("schema") != "merlin-cace-trust-store-v1"
        or not isinstance(document.get("keys"), list)
    ):
        raise PermissionError("CACE Merlin RSI trust store schema mismatch")
    approved: dict[str, str] = {}
    for entry in document["keys"]:
        if (
            not isinstance(entry, Mapping)
            or set(entry) != {"key_id", "verifier_id", "status"}
            or entry.get("verifier_id") != "cace"
            or entry.get("status") != "active"
        ):
            raise PermissionError("CACE trust store contains an invalid or inactive key")
        key_id = entry.get("key_id")
        if not isinstance(key_id, str) or not re.fullmatch(r"ed25519:[0-9a-f]{64}", key_id):
            raise PermissionError("CACE trust store key ID is invalid")
        if key_id in approved:
            raise PermissionError("CACE trust store contains duplicate key IDs")
        approved[key_id] = "cace"
    if not approved:
        raise PermissionError("CACE trust store has no active verifier keys")
    return approved


def verify_merlin_rsi_attestation(
    *,
    bundle_payload: Mapping[str, Any],
    attestation_payload: Mapping[str, Any],
    expected_claim_id: str,
    expected_bindings: Mapping[str, Any],
    artifact_bytes_b64: Mapping[str, str],
    trust_store_json: str,
    trust_store_sha256: str,
    cace_app_root: str | Path = "/opt/cace-web/current",
) -> dict[str, Any]:
    """Verify an exact CACE EvidenceBundle and independently pinned CACE signature."""
    if not isinstance(expected_claim_id, str) or not expected_claim_id.strip():
        raise ValueError("expected_claim_id must be non-empty")
    if not isinstance(expected_bindings, Mapping):
        raise ValueError("expected_bindings must be an object")

    root = Path(cace_app_root)
    if not (root / "cace_studio" / "core").is_dir():
        raise RuntimeError("CACE core runtime is unavailable at the configured application root")
    import sys
    root_text = str(root.resolve())
    if root_text not in sys.path:
        sys.path.insert(0, root_text)

    try:
        from cace_studio.core.attestation import attestation_from_payload, verify_attestation
        from cace_studio.core.evidence_ledger import bundle_from_payload, verify_bundle
        from cace_studio.core.reproducibility import canonical_json_bytes
    except ImportError as exc:
        raise RuntimeError("CACE core attestation dependencies are unavailable") from exc

    approved = _approved_keys(trust_store_json, trust_store_sha256)
    bundle = bundle_from_payload(bundle_payload)
    if not isinstance(artifact_bytes_b64, Mapping):
        raise ValueError("artifact_bytes_b64 must map artifact IDs to base64 bytes")
    if set(artifact_bytes_b64) != {item.artifact_id for item in bundle.artifacts}:
        raise PermissionError("artifact byte IDs do not exactly match the CACE EvidenceBundle")
    artifact_bytes: dict[str, bytes] = {}
    total_bytes = 0
    for artifact_id, encoded in artifact_bytes_b64.items():
        if not isinstance(encoded, str) or len(encoded) > 14_000_000:
            raise ValueError("each base64 artifact must be a bounded string")
        try:
            raw = base64.b64decode(encoded.encode("ascii"), validate=True)
        except Exception as exc:
            raise ValueError("artifact bytes must use canonical base64") from exc
        total_bytes += len(raw)
        if total_bytes > 10 * 1024 * 1024:
            raise ValueError("CACE RSI verification payload exceeds the 10 MiB limit")
        artifact_bytes[artifact_id] = raw
    bundle_sha256 = verify_bundle(bundle, artifact_bytes=artifact_bytes)
    if dict(bundle.bindings) != dict(expected_bindings):
        raise PermissionError("CACE EvidenceBundle bindings do not match the expected RSI evidence")
    attestation = attestation_from_payload(attestation_payload)
    key_id = verify_attestation(attestation)
    statement = attestation.statement

    if statement.verifier_id != "cace":
        raise PermissionError("attestation verifier identity is not CACE")
    if statement.verifier_key_id != key_id or approved.get(key_id) != "cace":
        raise PermissionError("attestation signing key is not independently pinned by CACE")
    if statement.purpose != "independent-reproduction":
        raise PermissionError("CACE attestation purpose is not independent reproduction")
    if statement.claim_id != expected_claim_id:
        raise PermissionError("CACE attestation claim ID mismatch")
    if statement.bundle_sha256 != bundle_sha256:
        raise PermissionError("CACE attestation does not bind the exact verified bundle")
    if dict(statement.bindings) != dict(expected_bindings):
        raise PermissionError("CACE attestation bindings do not match the expected RSI evidence")

    attestation_sha256 = _sha256(canonical_json_bytes(attestation.payload()))
    return {
        "schema": "cace-merlin-rsi-verification-result-v1",
        "verified": True,
        "verifier_id": "cace",
        "verifier_key_id": key_id,
        "claim_id": expected_claim_id,
        "bundle_sha256": bundle_sha256,
        "attestation_sha256": attestation_sha256,
        "statement_sha256": statement.statement_sha256,
        "artifact_count": len(artifact_bytes),
        "artifact_bytes_verified": total_bytes,
        "proof_effect": "none",
        "authority": "verification-only",
    }
