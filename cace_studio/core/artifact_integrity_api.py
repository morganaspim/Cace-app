"""Authenticated, source-bound CACE artifact-integrity verification API.

This protocol verifies exact source-commit existence, canonical evidence-bundle
identity, and supplied artifact bytes before signing an artifact-integrity
attestation. It is provenance-only: it never establishes semantic correctness
or mathematical proof qualification.
"""
from __future__ import annotations

import base64
import binascii
import hmac
import json
import os
import re
from datetime import datetime, timezone
from typing import Any, Callable, Mapping
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from fastapi import APIRouter, Body, Header, HTTPException

from cace_studio.core.attestation import (
    AttestationStatement,
    sign_attestation,
    verify_attestation,
    public_key_id,
)
from cace_studio.core.evidence_ledger import bundle_from_payload, verify_bundle

REQUEST_SCHEMA = "cace-artifact-integrity-request-v1"
PROTOCOL = "cace-artifact-integrity-v1"
MAX_ARTIFACT_BYTES = 8 * 1024 * 1024
MAX_TOTAL_ARTIFACT_BYTES = 24 * 1024 * 1024
_REPO_RE = re.compile(r"^[A-Za-z0-9_.-]{1,100}/[A-Za-z0-9_.-]{1,100}$")
_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")


class ArtifactIntegrityError(ValueError):
    """Raised when source or artifact integrity checks fail closed."""


def _nonempty_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value or value.strip() != value:
        raise ArtifactIntegrityError(f"{field} must be a non-empty canonical string")
    return value


def _exact_keys(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    actual = set(value)
    if actual != expected:
        raise ArtifactIntegrityError(
            f"{label} keys mismatch; missing={sorted(expected-actual)}, "
            f"extra={sorted(actual-expected)}"
        )


def _decode_artifacts(raw: Any, expected_ids: set[str]) -> dict[str, bytes]:
    if not isinstance(raw, dict) or set(raw) != expected_ids:
        raise ArtifactIntegrityError("artifact_bytes_base64 must contain exactly the bundle artifact IDs")
    decoded: dict[str, bytes] = {}
    total = 0
    for artifact_id, encoded in raw.items():
        if not isinstance(encoded, str):
            raise ArtifactIntegrityError(f"artifact {artifact_id!r} bytes must be base64 text")
        try:
            data = base64.b64decode(encoded.encode("ascii"), validate=True)
        except (UnicodeEncodeError, binascii.Error, ValueError) as exc:
            raise ArtifactIntegrityError(f"artifact {artifact_id!r} has invalid base64") from exc
        if base64.b64encode(data).decode("ascii") != encoded:
            raise ArtifactIntegrityError(f"artifact {artifact_id!r} base64 is not canonical")
        if len(data) > MAX_ARTIFACT_BYTES:
            raise ArtifactIntegrityError(f"artifact {artifact_id!r} exceeds the per-artifact limit")
        total += len(data)
        if total > MAX_TOTAL_ARTIFACT_BYTES:
            raise ArtifactIntegrityError("artifact payload exceeds the total byte limit")
        decoded[artifact_id] = data
    return decoded


def create_artifact_integrity_attestation(
    payload: Mapping[str, Any],
    *,
    private_key_pem: bytes,
    verifier_id: str,
    commit_resolver: Callable[[str, str], str],
    created_at_utc: str | None = None,
) -> dict[str, Any]:
    """Verify exact source and bytes, then sign an integrity-only receipt."""
    if not isinstance(payload, Mapping):
        raise ArtifactIntegrityError("request must be an object")
    _exact_keys(
        payload,
        {
            "schema",
            "source_repository",
            "source_commit",
            "artifact_kind",
            "tool_version",
            "bundle",
            "artifact_bytes_base64",
        },
        "request",
    )
    if payload["schema"] != REQUEST_SCHEMA:
        raise ArtifactIntegrityError(f"unsupported request schema: {payload['schema']!r}")

    repository = _nonempty_string(payload["source_repository"], "source_repository")
    commit = _nonempty_string(payload["source_commit"], "source_commit")
    artifact_kind = _nonempty_string(payload["artifact_kind"], "artifact_kind")
    tool_version = _nonempty_string(payload["tool_version"], "tool_version")
    if not _REPO_RE.fullmatch(repository):
        raise ArtifactIntegrityError("source_repository must use owner/repository form")
    if not _COMMIT_RE.fullmatch(commit):
        raise ArtifactIntegrityError("source_commit must be a full lowercase 40-character Git SHA")

    bundle_raw = payload["bundle"]
    bundle = bundle_from_payload(bundle_raw)
    expected_bindings = {
        "source_repository": repository,
        "source_commit": commit,
        "artifact_kind": artifact_kind,
        "tool_version": tool_version,
    }
    for key, expected in expected_bindings.items():
        if bundle.bindings.get(key) != expected:
            raise ArtifactIntegrityError(f"bundle binding {key!r} does not match request")
    artifact_ids = {item.artifact_id for item in bundle.artifacts}
    artifact_bytes = _decode_artifacts(payload["artifact_bytes_base64"], artifact_ids)
    bundle_digest = verify_bundle(bundle, artifact_bytes=artifact_bytes)

    # The resolver is supplied by the API boundary and must query GitHub's
    # authenticated commit endpoint; caller-provided SHA syntax is not evidence.
    resolved_sha = commit_resolver(repository, commit)
    if resolved_sha != commit:
        raise ArtifactIntegrityError("GitHub commit lookup did not return the exact requested SHA")

    key_id = public_key_id_from_private(private_key_pem)
    timestamp = created_at_utc or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    bindings = {
        **expected_bindings,
        "protocol": PROTOCOL,
        "merkle_root_sha256": bundle.merkle_root_sha256,
        "artifact_ids": sorted(artifact_ids),
        "artifact_count": len(artifact_ids),
        "source_commit_resolved": True,
        "artifact_bytes_verified": True,
    }
    statement = AttestationStatement(
        verifier_id=_nonempty_string(verifier_id, "verifier_id"),
        verifier_key_id=key_id,
        claim_id=f"artifact-integrity:{repository}@{commit}:{artifact_kind}",
        bundle_sha256=bundle_digest,
        created_at_utc=timestamp,
        purpose="artifact-integrity",
        bindings=bindings,
    )
    signed = sign_attestation(statement, private_key_pem)
    verify_attestation(signed)
    return {
        "schema": "cace-artifact-integrity-response-v1",
        "status": "verified",
        "proof_effect": "none",
        "qualification": False,
        "semantic_correctness": "not_established",
        "bundle_sha256": bundle_digest,
        "merkle_root_sha256": bundle.merkle_root_sha256,
        "source_repository": repository,
        "source_commit": commit,
        "artifact_kind": artifact_kind,
        "tool_version": tool_version,
        "verifier_id": verifier_id,
        "verifier_key_id": key_id,
        "attestation": signed.payload(),
        "checks": {
            "github_commit_exact_match": True,
            "bundle_digest_recomputed": True,
            "merkle_root_recomputed": True,
            "all_artifact_bytes_verified": True,
            "signature_self_verified": True,
        },
    }


def public_key_id_from_private(private_key_pem: bytes) -> str:
    # sign_attestation independently checks this ID against the private key;
    # derive it through the vetted public-key serialization helper.
    from cryptography.hazmat.primitives import serialization

    key = serialization.load_pem_private_key(private_key_pem, password=None)
    public_pem = key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return public_key_id(public_pem)


def _github_commit_resolver(repository: str, commit: str, token: str) -> str:
    request = Request(
        f"https://api.github.com/repos/{repository}/commits/{commit}",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "CACE-artifact-integrity-verifier",
        },
    )
    try:
        with urlopen(request, timeout=8) as response:
            document = json.loads(response.read(256 * 1024).decode("utf-8"))
    except HTTPError as exc:
        if exc.code == 404:
            raise ArtifactIntegrityError("source commit is not visible in the configured GitHub repository") from exc
        raise RuntimeError(f"GitHub commit lookup failed with HTTP {exc.code}") from exc
    except (URLError, TimeoutError, OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("GitHub commit lookup is unavailable") from exc
    resolved = document.get("sha") if isinstance(document, dict) else None
    return resolved if isinstance(resolved, str) else ""


router = APIRouter()


@router.post("/api/verification/artifact-integrity")
def verify_artifact_integrity(
    payload: dict[str, Any] = Body(...),
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    expected_token = os.getenv("CACE_ARTIFACT_INTEGRITY_TOKEN")
    github_token = os.getenv("CACE_GITHUB_API_TOKEN")
    private_key_b64 = os.getenv("CACE_ARTIFACT_INTEGRITY_PRIVATE_KEY_B64")
    expected_key_id = os.getenv("CACE_ARTIFACT_INTEGRITY_TRUSTED_KEY_ID")
    verifier_id = os.getenv("CACE_ARTIFACT_INTEGRITY_VERIFIER_ID")
    if not all((expected_token, github_token, private_key_b64, expected_key_id, verifier_id)):
        raise HTTPException(status_code=503, detail="artifact-integrity verifier is not configured")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="bearer authentication required")
    supplied_token = authorization[len("Bearer "):]
    if not hmac.compare_digest(supplied_token, expected_token):
        raise HTTPException(status_code=401, detail="invalid bearer credential")
    try:
        private_key_pem = base64.b64decode(private_key_b64.encode("ascii"), validate=True)
        actual_key_id = public_key_id_from_private(private_key_pem)
        if not hmac.compare_digest(actual_key_id, expected_key_id):
            raise HTTPException(status_code=503, detail="configured signer does not match pinned verifier key ID")
        result = create_artifact_integrity_attestation(
            payload,
            private_key_pem=private_key_pem,
            verifier_id=verifier_id,
            commit_resolver=lambda repo, sha: _github_commit_resolver(repo, sha, github_token),
        )
        return result
    except ArtifactIntegrityError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"independent verifier unavailable: {type(exc).__name__}") from exc
