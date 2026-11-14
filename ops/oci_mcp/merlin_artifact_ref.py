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


def _exact_provenance(value: Any) -> dict[str, str]:
    fields = {"schema", "source_repo", "source_commit", "artifact_id", "artifact_kind", "artifact_schema"}
    if not isinstance(value, Mapping) or set(value) != fields:
        raise PermissionError("Merlin resolver must return the exact immutable artifact provenance fields")
    provenance = dict(value)
    if provenance.get("schema") != "merlin-artifact-provenance/1":
        raise PermissionError("unsupported Merlin artifact provenance schema")
    if provenance.get("source_repo") != "Mannyspiro/expert-robot":
        raise PermissionError("Merlin artifact provenance source repository is not allowlisted")
    if not isinstance(provenance.get("source_commit"), str) or not re.fullmatch(r"[0-9a-f]{40}", provenance["source_commit"]):
        raise PermissionError("Merlin artifact provenance source commit is not a full Git SHA")
    for field in ("artifact_id", "artifact_kind", "artifact_schema"):
        item = provenance.get(field)
        if not isinstance(item, str) or not item.strip() or len(item) > 256:
            raise PermissionError(f"Merlin artifact provenance {field} is invalid")
    return provenance


def resolve_merlin_artifact_bytes(
    artifact_ref: Mapping[str, Any],
    *,
    resolver: Callable[[dict[str, Any]], Mapping[str, Any]],
) -> tuple[dict[str, Any], bytes, dict[str, str]]:
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
    if (
        not isinstance(resolution, Mapping)
        or resolution.get("schema") != "merlin-artifact-resolution/1"
        or resolution.get("verified") is not True
    ):
        raise PermissionError("Merlin did not return a verified canonical historical resolution")
    if (
        resolution.get("artifact_ref") != ref
        or type(resolution.get("is_current")) is not bool
        or isinstance(resolution.get("size_bytes"), bool)
        or not isinstance(resolution.get("size_bytes"), int)
    ):
        raise PermissionError("Merlin historical resolution does not bind the exact reference metadata")
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
    provenance = _exact_provenance(resolution.get("provenance"))
    return ref, raw, provenance


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


def _artifact_map(
    bundle: Any, *, artifact_ref: Mapping[str, Any], artifact_id: str,
    artifact_kind: str, artifact_schema: str,
) -> dict[str, Any]:
    items = list(bundle.artifacts)
    if len(items) != 1:
        raise PermissionError("ArtifactRef attestation requires exactly one EvidenceBundle artifact")
    item = items[0]
    if getattr(item, "artifact_id", None) != artifact_id:
        raise PermissionError("EvidenceBundle artifact ID does not match requested identity")
    if getattr(item, "role", None) != artifact_kind:
        raise PermissionError("EvidenceBundle artifact role does not match artifact_kind")
    if getattr(item, "path", None) != artifact_ref["logical_path"]:
        raise PermissionError("EvidenceBundle artifact path does not match ArtifactRef logical_path")
    metadata = getattr(item, "metadata", None)
    if not isinstance(metadata, Mapping) or metadata.get("artifact_schema") != artifact_schema:
        raise PermissionError("EvidenceBundle artifact metadata does not bind artifact_schema")
    if getattr(item, "sha256", None) != artifact_ref["sha256"]:
        raise PermissionError("EvidenceBundle artifact digest does not match ArtifactRef")
    return {artifact_id: item}


def _open_secure_artifact_key_parent(private_key_path: str):
    """Open/create every parent component without following symlinks."""
    import os
    import stat
    from pathlib import Path

    if not hasattr(os, "O_NOFOLLOW") or not hasattr(os, "O_DIRECTORY"):
        raise RuntimeError("secure ArtifactRef key custody requires O_NOFOLLOW and O_DIRECTORY")
    path = Path(os.path.abspath(os.fspath(private_key_path)))
    if not path.name or path.name in {".", ".."}:
        raise ValueError("ArtifactRef signing key path must name a file")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
    fd = os.open(path.anchor, flags)
    try:
        allowed_owners = {0, os.geteuid()}
        for component in path.parent.parts[1:]:
            try:
                child = os.open(component, flags, dir_fd=fd)
            except FileNotFoundError:
                try:
                    os.mkdir(component, 0o700, dir_fd=fd)
                    os.fsync(fd)
                except FileExistsError:
                    pass
                child = os.open(component, flags, dir_fd=fd)
            info = os.fstat(child)
            if not stat.S_ISDIR(info.st_mode):
                os.close(child)
                raise PermissionError("ArtifactRef key parent component is not a directory")
            if info.st_uid not in allowed_owners:
                os.close(child)
                raise PermissionError("ArtifactRef key parent has an unexpected owner")
            if info.st_mode & 0o022 and not info.st_mode & stat.S_ISVTX:
                os.close(child)
                raise PermissionError("ArtifactRef key parent is group/world writable without sticky protection")
            os.close(fd)
            fd = child
        final_info = os.fstat(fd)
        if final_info.st_uid not in allowed_owners:
            raise PermissionError("ArtifactRef key directory has an unexpected owner")
        if final_info.st_mode & 0o022:
            raise PermissionError("ArtifactRef key directory must not be group/world writable")
        os.fchmod(fd, 0o700)
        return fd, path.name, path
    except Exception:
        os.close(fd)
        raise


def _read_artifact_key_at(parent_fd: int, key_name: str) -> bytes | None:
    """Read an existing key through its pinned directory descriptor."""
    import os
    import stat

    flags = os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
    try:
        fd = os.open(key_name, flags, dir_fd=parent_fd)
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise PermissionError("unable to open ArtifactRef key without following symlinks") from exc
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            raise PermissionError("ArtifactRef signing key must be a regular file")
        if info.st_uid != os.geteuid():
            raise PermissionError("ArtifactRef signing key has an unexpected owner")
        if info.st_nlink != 1:
            raise PermissionError("ArtifactRef signing key must not have additional hard links")
        if info.st_size < 1 or info.st_size > 65536:
            raise PermissionError("ArtifactRef signing key file has an invalid size")
        os.fchmod(fd, 0o600)
        chunks = []
        total = 0
        while True:
            chunk = os.read(fd, min(8192, 65537 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > 65536:
                raise PermissionError("ArtifactRef signing key file is unexpectedly large")
        return b"".join(chunks)
    finally:
        os.close(fd)


def initialize_merlin_artifact_ref_attestor(
    *, private_key_path: str, cace_app_root: str = "/opt/cace-web/current",
) -> dict[str, Any]:
    """Create a separate Ed25519 ArtifactRef key atomically, once, without path traversal."""
    import os
    import secrets
    ( _, _, _, _, _, _, _ ) = _load_core(cace_app_root)
    from cace_studio.core.attestation import generate_ed25519_keypair_pem, public_key_id

    parent_fd, key_name, path = _open_secure_artifact_key_parent(private_key_path)
    created = False
    try:
        private_pem = _read_artifact_key_at(parent_fd, key_name)
        if private_pem is None:
            candidate, _ = generate_ed25519_keypair_pem()
            temp_name = f".{key_name}.tmp-{secrets.token_hex(16)}"
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
            temp_fd = os.open(temp_name, flags, 0o600, dir_fd=parent_fd)
            try:
                view = memoryview(candidate)
                while view:
                    written = os.write(temp_fd, view)
                    if written <= 0:
                        raise OSError("short write while creating ArtifactRef signing key")
                    view = view[written:]
                os.fsync(temp_fd)
            finally:
                os.close(temp_fd)
            try:
                # link() is atomic and refuses to replace an existing key.
                os.link(
                    temp_name, key_name, src_dir_fd=parent_fd,
                    dst_dir_fd=parent_fd, follow_symlinks=False,
                )
                os.fsync(parent_fd)
                created = True
                private_pem = candidate
            except FileExistsError:
                private_pem = _read_artifact_key_at(parent_fd, key_name)
                if private_pem is None:
                    raise PermissionError("ArtifactRef key creation raced with an invalid replacement")
            finally:
                try:
                    os.unlink(temp_name, dir_fd=parent_fd)
                except FileNotFoundError:
                    pass
        if private_pem is None:
            raise PermissionError("ArtifactRef signing key could not be initialized")
    finally:
        os.close(parent_fd)

    from cryptography.hazmat.primitives import serialization
    key = serialization.load_pem_private_key(private_pem, password=None)
    public_pem = key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    key_id = public_key_id(public_pem)
    return {
        "schema": "cace-merlin-artifact-ref-key-initialization-v1",
        "created": created, "key_path": str(path),
        "verifier_id": "cace", "verifier_key_id": key_id,
        "public_key_pem": public_pem.decode("ascii"),
        "private_key_mode": "0600", "proof_effect": "none",
    }


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
    ref, raw, provenance = resolve_merlin_artifact_bytes(artifact_ref, resolver=resolver)
    expected_provenance = {
        "schema": "merlin-artifact-provenance/1",
        "source_repo": source_repo, "source_commit": source_commit,
        "artifact_id": artifact_id, "artifact_kind": artifact_kind,
        "artifact_schema": artifact_schema,
    }
    if provenance != expected_provenance:
        raise PermissionError("caller-supplied source/artifact identity does not match Merlin's immutable provenance")
    bindings = _expected_bindings(
        artifact_ref=ref, source_repo=source_repo, source_commit=source_commit,
        artifact_id=artifact_id, artifact_kind=artifact_kind, artifact_schema=artifact_schema,
        size_bytes=len(raw), content_sha256=_sha256(raw),
    )
    bundle = bundle_from_payload(bundle_payload)
    if dict(bundle.bindings) != bindings:
        raise PermissionError("EvidenceBundle bindings do not exactly match ArtifactRef identity")
    artifacts = _artifact_map(bundle, artifact_ref=ref, artifact_id=artifact_id, artifact_kind=artifact_kind, artifact_schema=artifact_schema)
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


def _approved_artifact_ref_keys(trust_store_json: str, trust_store_sha256: str) -> set[str]:
    if not isinstance(trust_store_json, str) or not trust_store_json:
        raise PermissionError("CACE ArtifactRef trust store is not configured")
    if not isinstance(trust_store_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", trust_store_sha256):
        raise PermissionError("CACE ArtifactRef trust store digest is invalid")
    if _sha256(trust_store_json.encode("utf-8")) != trust_store_sha256:
        raise PermissionError("CACE ArtifactRef trust store digest mismatch")
    try:
        trust = json.loads(trust_store_json)
    except ValueError as exc:
        raise PermissionError("CACE ArtifactRef trust store is invalid JSON") from exc
    if not isinstance(trust, Mapping) or set(trust) != {"schema", "keys"} or trust.get("schema") != "merlin-cace-trust-store-v1" or not isinstance(trust.get("keys"), list):
        raise PermissionError("CACE ArtifactRef trust store schema mismatch")
    approved: set[str] = set()
    for entry in trust["keys"]:
        if not isinstance(entry, Mapping) or set(entry) != {"key_id", "verifier_id", "status"} or entry.get("verifier_id") != "cace" or entry.get("status") != "active":
            raise PermissionError("CACE ArtifactRef trust store contains invalid key entry")
        key_id = entry.get("key_id")
        if not isinstance(key_id, str) or not re.fullmatch(r"ed25519:[0-9a-f]{64}", key_id):
            raise PermissionError("CACE ArtifactRef trust key ID is invalid")
        if key_id in approved:
            raise PermissionError("CACE ArtifactRef trust store contains duplicate key IDs")
        approved.add(key_id)
    if not approved:
        raise PermissionError("CACE ArtifactRef trust store has no active keys")
    return approved


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
    approved = _approved_artifact_ref_keys(trust_store_json, trust_store_sha256)
    ref, raw, provenance = resolve_merlin_artifact_bytes(artifact_ref, resolver=resolver)
    expected_provenance = {
        "schema": "merlin-artifact-provenance/1",
        "source_repo": source_repo, "source_commit": source_commit,
        "artifact_id": artifact_id, "artifact_kind": artifact_kind,
        "artifact_schema": artifact_schema,
    }
    if provenance != expected_provenance:
        raise PermissionError("caller-supplied source/artifact identity does not match Merlin's immutable provenance")
    bindings = _expected_bindings(
        artifact_ref=ref, source_repo=source_repo, source_commit=source_commit,
        artifact_id=artifact_id, artifact_kind=artifact_kind, artifact_schema=artifact_schema,
        size_bytes=len(raw), content_sha256=_sha256(raw),
    )
    bundle = bundle_from_payload(bundle_payload)
    if dict(bundle.bindings) != bindings or set(_artifact_map(bundle, artifact_ref=ref, artifact_id=artifact_id, artifact_kind=artifact_kind, artifact_schema=artifact_schema)) != {artifact_id}:
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
