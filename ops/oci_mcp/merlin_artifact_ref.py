"""CACE-owned attestation for immutable Merlin ArtifactRef identities.

This path is deliberately separate from RSI reproduction. It verifies artifact
identity and exact historical bytes only; it never grants proof/promotion authority.
"""
from __future__ import annotations

import base64
import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Mapping

ARTIFACT_REF_SCHEMA = "merlin-artifact-ref/1"
REQUEST_SCHEMA = "merlin-artifact-resolution-request/1"
RESPONSE_SCHEMA = "merlin-artifact-resolution/2"
PURPOSE = "artifact-integrity"
MAX_ARTIFACT_BYTES = 10 * 1024 * 1024


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _exact_ref(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping) or set(value) != {
        "schema", "project_id", "logical_path", "version", "sha256"
    }:
        raise ValueError("ArtifactRef must contain the exact canonical field set")
    ref = dict(value)
    if ref["schema"] != ARTIFACT_REF_SCHEMA:
        raise ValueError("unsupported ArtifactRef schema")
    for field in ("project_id", "logical_path"):
        item = ref[field]
        if not isinstance(item, str) or not item.strip() or len(item) > 1024:
            raise ValueError(f"ArtifactRef {field} must be a non-empty bounded string")
    if isinstance(ref["version"], bool) or not isinstance(ref["version"], int) or ref["version"] < 1:
        raise ValueError("ArtifactRef version must be a positive integer")
    if not isinstance(ref["sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", ref["sha256"]):
        raise ValueError("ArtifactRef sha256 must be lowercase SHA-256")
    return ref


def _decode_canonical_b64(encoded: Any) -> bytes:
    if not isinstance(encoded, str) or len(encoded) > 14_000_000:
        raise ValueError("resolved artifact content must be a bounded base64 string")
    try:
        raw = base64.b64decode(encoded.encode("ascii"), validate=True)
    except Exception as exc:
        raise ValueError("resolved artifact content is not valid base64") from exc
    if base64.b64encode(raw).decode("ascii") != encoded:
        raise ValueError("resolved artifact content is not canonical base64")
    if len(raw) > MAX_ARTIFACT_BYTES:
        raise ValueError("resolved artifact exceeds the 10 MiB limit")
    return raw


def resolve_merlin_artifact_bytes(
    artifact_ref: Mapping[str, Any],
    *,
    resolver: Callable[[dict[str, Any]], Mapping[str, Any]],
) -> tuple[dict[str, Any], bytes]:
    """Ask an injected authenticated Merlin transport for exact historical bytes."""
    ref = _exact_ref(artifact_ref)
    if not callable(resolver):
        raise RuntimeError("authenticated Merlin resolver transport is unavailable")
    response = resolver(ref)
    if not isinstance(response, Mapping):
        raise PermissionError("Merlin resolver response must be an object")
    if response.get("schema") != RESPONSE_SCHEMA:
        raise PermissionError("Merlin resolver response schema mismatch")
    if response.get("artifact_ref") != ref:
        raise PermissionError("Merlin resolver returned a substituted ArtifactRef")
    if response.get("authority") != "read_only_artifact_bytes":
        raise PermissionError("Merlin resolver authority is not read-only artifact bytes")
    resolution = response.get("resolution")
    if not isinstance(resolution, Mapping) or resolution.get("verified") is not True:
        raise PermissionError("Merlin did not verify the historical artifact row")
    if resolution.get("artifact_ref") != ref or resolution.get("is_current") not in (True, False):
        raise PermissionError("Merlin historical resolution does not bind the exact reference")
    if isinstance(response.get("size_bytes"), bool) or not isinstance(response.get("size_bytes"), int):
        raise PermissionError("Merlin resolver size is invalid")
    if response["size_bytes"] < 0 or response["size_bytes"] > MAX_ARTIFACT_BYTES:
        raise PermissionError("Merlin resolver size is outside the accepted limit")
    raw = _decode_canonical_b64(response.get("content_b64"))
    digest = _sha256(raw)
    if len(raw) != response["size_bytes"] or digest != ref["sha256"]:
        raise PermissionError("independently retrieved bytes do not match ArtifactRef size/digest")
    if response.get("content_sha256") != digest:
        raise PermissionError("Merlin resolver content digest mismatch")
    if resolution.get("size_bytes") != len(raw):
        raise PermissionError("Merlin resolution metadata size mismatch")
    return ref, raw


def _load_core(cace_app_root: str):
    from pathlib import Path
    import sys
    root = Path(cace_app_root)
    if not (root / "cace_studio" / "core").is_dir():
        raise RuntimeError("CACE core runtime is unavailable")
    root_text = str(root.resolve())
    if root_text not in sys.path:
        sys.path.insert(0, root_text)
    try:
        from cace_studio.core.attestation import (
            AttestationStatement, public_key_id, sign_attestation,
            attestation_from_payload, verify_attestation,
        )
        from cace_studio.core.evidence_ledger import bundle_from_payload, verify_bundle
    except ImportError as exc:
        raise RuntimeError("CACE core attestation/evidence dependencies are unavailable") from exc
    return (AttestationStatement, public_key_id, sign_attestation,
            attestation_from_payload, verify_attestation, bundle_from_payload, verify_bundle)


def _artifact_map(bundle: Any) -> dict[str, Any]:
    items = list(bundle.artifacts)
    if len(items) != 1:
        raise PermissionError("ArtifactRef attestation requires exactly one EvidenceBundle artifact")
    item = items[0]
    artifact_id = getattr(item, "artifact_id", None)
    if not isinstance(artifact_id, str) or not artifact_id:
        raise PermissionError("EvidenceBundle artifact identity is malformed")
    return {artifact_id: item}


def _expected_bindings(
    *, artifact_ref: Mapping[str, Any], source_repo: str, source_commit: str,
    artifact_id: str, artifact_kind: str, artifact_schema: str,
    size_bytes: int, content_sha256: str,
) -> dict[str, Any]:
    ref = _exact_ref(artifact_ref)
    if source_repo != "Mannyspiro/expert-robot":
        raise PermissionError("ArtifactRef source repository is not allowlisted")
    if not isinstance(source_commit, str) or not re.fullmatch(r"[0-9a-f]{40}", source_commit):
        raise ValueError("source_commit must be a full lowercase Git commit SHA")
    for field, value in (("artifact_id", artifact_id), ("artifact_kind", artifact_kind),
                         ("artifact_schema", artifact_schema)):
        if not isinstance(value, str) or not value.strip() or len(value) > 256:
            raise ValueError(f"{field} must be a non-empty bounded string")
    if isinstance(size_bytes, bool) or not isinstance(size_bytes, int) or not 0 <= size_bytes <= MAX_ARTIFACT_BYTES:
        raise ValueError("size_bytes is outside the accepted limit")
    if not isinstance(content_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", content_sha256):
        raise ValueError("content_sha256 must be lowercase SHA-256")
    if content_sha256 != ref["sha256"]:
        raise PermissionError("artifact content digest must equal ArtifactRef digest")
    return {
        "schema": "cace-merlin-artifact-integrity-bindings-v1",
        "artifact_ref": ref,
        "source_repo": source_repo,
        "source_commit": source_commit,
        "artifact_id": artifact_id,
        "artifact_kind": artifact_kind,
        "artifact_schema": artifact_schema,
        "size_bytes": size_bytes,
        "content_sha256": content_sha256,
        "authority": "verification-only",
    }


def attest_merlin_artifact_ref(
    *, bundle_payload: Mapping[str, Any], artifact_ref: Mapping[str, Any],
    source_repo: str, source_commit: str, artifact_id: str,
    artifact_kind: str, artifact_schema: str,
    resolver: Callable[[dict[str, Any]], Mapping[str, Any]],
    private_key_pem: str | bytes, cace_app_root: str = "/opt/cace-web/current",
) -> dict[str, Any]:
    """Independently resolve exact historical bytes, verify bundle, and sign bindings."""
    (Statement, key_id_fn, sign, _, _, bundle_from_payload, verify_bundle) = _load_core(cace_app_root)
    ref, raw = resolve_merlin_artifact_bytes(artifact_ref, resolver=resolver)
    bindings = _expected_bindings(
        artifact_ref=ref, source_repo=source_repo, source_commit=source_commit,
        artifact_id=artifact_id, artifact_kind=artifact_kind, artifact_schema=artifact_schema,
        size_bytes=len(raw), content_sha256=_sha256(raw),
    )
    bundle = bundle_from_payload(bundle_payload)
    if dict(bundle.bindings) != bindings:
        raise PermissionError("EvidenceBundle bindings do not exactly match ArtifactRef identity")
    artifacts = _artifact_map(bundle)
    if set(artifacts) != {artifact_id}:
        raise PermissionError("EvidenceBundle artifact ID does not match requested artifact")
    bundle_sha = verify_bundle(bundle, artifact_bytes={artifact_id: raw})
    if not isinstance(private_key_pem, (str, bytes)) or not private_key_pem:
        raise PermissionError("CACE ArtifactRef signing key is not configured")
    from cryptography.hazmat.primitives import serialization
    pem = private_key_pem.encode("ascii") if isinstance(private_key_pem, str) else private_key_pem
    key = serialization.load_pem_private_key(pem, password=None)
    public_pem = key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    statement = Statement(
        verifier_id="cace", verifier_key_id=key_id_fn(public_pem),
        claim_id=artifact_id, bundle_sha256=bundle_sha,
        created_at_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        purpose=PURPOSE, bindings=bindings,
    )
    signed = sign(statement, pem)
    return {
        "schema": "cace-merlin-artifact-ref-attestation-result-v1",
        "attestation": signed.payload(), "verified_bundle_sha256": bundle_sha,
        "artifact_ref": ref, "artifact_id": artifact_id, "size_bytes": len(raw),
        "content_sha256": _sha256(raw), "verifier_key_id": statement.verifier_key_id,
        "purpose": PURPOSE, "proof_effect": "none", "authority": "verification-only",
    }


def verify_merlin_artifact_ref(
    *, bundle_payload: Mapping[str, Any], attestation_payload: Mapping[str, Any],
    artifact_ref: Mapping[str, Any], source_repo: str, source_commit: str,
    artifact_id: str, artifact_kind: str, artifact_schema: str,
    resolver: Callable[[dict[str, Any]], Mapping[str, Any]],
    trust_store_json: str, trust_store_sha256: str,
    cace_app_root: str = "/opt/cace-web/current",
) -> dict[str, Any]:
    """Re-resolve bytes and verify the signed statement against pinned CACE trust."""
    ( _, _, _, from_payload, verify_sig, bundle_from_payload, verify_bundle) = _load_core(cace_app_root)
    if not trust_store_json or _sha256(trust_store_json.encode("utf-8")) != trust_store_sha256:
        raise PermissionError("CACE ArtifactRef trust store is missing or digest-mismatched")
    try:
        trust = json.loads(trust_store_json)
    except ValueError as exc:
        raise PermissionError("CACE ArtifactRef trust store is invalid JSON") from exc
    if not isinstance(trust, Mapping) or set(trust) != {"schema", "keys"} or trust.get("schema") != "merlin-cace-trust-store-v1" or not isinstance(trust.get("keys"), list):
        raise PermissionError("CACE ArtifactRef trust store schema mismatch")
    approved = set()
    for entry in trust["keys"]:
        if not isinstance(entry, Mapping) or set(entry) != {"key_id", "verifier_id", "status"} or entry.get("verifier_id") != "cace" or entry.get("status") != "active":
            raise PermissionError("CACE ArtifactRef trust store contains invalid key entry")
        key_id = entry.get("key_id")
        if not isinstance(key_id, str) or not re.fullmatch(r"ed25519:[0-9a-f]{64}", key_id):
            raise PermissionError("CACE ArtifactRef trust key ID is invalid")
        approved.add(key_id)
    if not approved:
        raise PermissionError("CACE ArtifactRef trust store has no active keys")
    ref, raw = resolve_merlin_artifact_bytes(artifact_ref, resolver=resolver)
    bindings = _expected_bindings(
        artifact_ref=ref, source_repo=source_repo, source_commit=source_commit,
        artifact_id=artifact_id, artifact_kind=artifact_kind, artifact_schema=artifact_schema,
        size_bytes=len(raw), content_sha256=_sha256(raw),
    )
    bundle = bundle_from_payload(bundle_payload)
    if dict(bundle.bindings) != bindings or set(_artifact_map(bundle)) != {artifact_id}:
        raise PermissionError("EvidenceBundle does not bind the exact ArtifactRef")
    bundle_sha = verify_bundle(bundle, artifact_bytes={artifact_id: raw})
    attestation = from_payload(attestation_payload)
    key_id = verify_sig(attestation)
    statement = attestation.statement
    if statement.verifier_id != "cace" or statement.verifier_key_id != key_id or key_id not in approved:
        raise PermissionError("ArtifactRef attestation signer is not independently pinned CACE")
    if statement.purpose != PURPOSE or statement.claim_id != artifact_id:
        raise PermissionError("ArtifactRef attestation purpose or artifact identity mismatch")
    if statement.bundle_sha256 != bundle_sha or dict(statement.bindings) != bindings:
        raise PermissionError("ArtifactRef attestation does not bind the exact verified bundle")
    created = datetime.strptime(statement.created_at_utc, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    if created > now + timedelta(minutes=5) or now - created > timedelta(days=30):
        raise PermissionError("ArtifactRef attestation timestamp is outside the accepted window")
    return {
        "schema": "cace-merlin-artifact-ref-verification-result-v1",
        "verified": True, "verifier_id": "cace", "verifier_key_id": key_id,
        "artifact_ref": ref, "artifact_id": artifact_id, "bundle_sha256": bundle_sha,
        "content_sha256": _sha256(raw), "size_bytes": len(raw),
        "purpose": PURPOSE, "proof_effect": "none", "authority": "verification-only",
    }
