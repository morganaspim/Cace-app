"""Independent verification adapter for Merlin RSI evidence bundles.

This module delegates bundle and signature semantics to CACE's own core
implementation. It does not create attestations, run candidate code, or grant
proof/promotion authority.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
from datetime import datetime, timedelta, timezone
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
    required_bindings = {
        "candidate_id",
        "candidate_digest",
        "benchmark_manifest_sha256",
        "evaluator_receipt_sha256",
        "source_repo",
        "source_commit",
        "authority",
    }
    if set(expected_bindings) != required_bindings:
        raise ValueError("expected_bindings must match the exact Merlin RSI evidence schema")
    if expected_bindings.get("candidate_id") != expected_claim_id:
        raise PermissionError("expected claim ID must match the candidate binding")
    if expected_bindings.get("authority") != "verification-only":
        raise PermissionError("CACE RSI verification cannot assert promotion authority")
    for field in ("candidate_digest", "benchmark_manifest_sha256", "evaluator_receipt_sha256"):
        value = expected_bindings.get(field)
        if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
            raise ValueError(f"{field} must be lowercase SHA-256")
    if expected_bindings.get("source_repo") != "Mannyspiro/expert-robot":
        raise PermissionError("CACE RSI source repository is not allowlisted")
    if not isinstance(expected_bindings.get("source_commit"), str) or not re.fullmatch(
        r"[0-9a-f]{40}", expected_bindings["source_commit"]
    ):
        raise ValueError("source_commit must be a 40-character lowercase Git commit")

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
    if len(artifact_bytes_b64) > 32:
        raise ValueError("CACE RSI verification accepts at most 32 artifacts")
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
        if base64.b64encode(raw).decode("ascii") != encoded:
            raise ValueError("artifact bytes must use canonical base64")
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
        raise PermissionError("CACE verification requires an independent-reproduction attestation")
    created_at = datetime.strptime(
        statement.created_at_utc, "%Y-%m-%dT%H:%M:%SZ"
    ).replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    if created_at > now + timedelta(minutes=5):
        raise PermissionError("CACE attestation timestamp is too far in the future")
    if now - created_at > timedelta(days=30):
        raise PermissionError("CACE attestation is outside the 30-day verification window")
    if statement.claim_id != expected_claim_id:
        raise PermissionError("CACE attestation claim ID mismatch")
    if statement.bundle_sha256 != bundle_sha256:
        raise PermissionError("CACE attestation does not bind the exact verified bundle")
    statement_bindings = dict(statement.bindings)
    runner_provenance = statement_bindings.pop("cace_runner_provenance", None)
    if statement_bindings != dict(expected_bindings):
        raise PermissionError("CACE attestation bindings do not match the expected RSI evidence")
    if statement.purpose == "independent-reproduction":
        required_provenance = {
            "schema", "repository", "run_id", "workflow_path", "workflow_commit",
            "runner_name", "job_id", "artifact_sha256", "source_repo",
            "source_commit", "benchmark_manifest_sha256",
        }
        if (not isinstance(runner_provenance, Mapping)
            or set(runner_provenance) != required_provenance
            or runner_provenance.get("schema") != "cace-oci-run-provenance-v1"
            or runner_provenance.get("repository") != "morganaspim/Cace-app"
            or runner_provenance.get("workflow_path") != ".github/workflows/merlin-oci-job-gateway.yml"
            or runner_provenance.get("runner_name") != "cace-oci-a1"
            or runner_provenance.get("source_repo") != expected_bindings.get("source_repo")
            or runner_provenance.get("source_commit") != expected_bindings.get("source_commit")
            or runner_provenance.get("benchmark_manifest_sha256") != expected_bindings.get("benchmark_manifest_sha256")
            or not isinstance(runner_provenance.get("run_id"), int)
            or not isinstance(runner_provenance.get("job_id"), int)
            or not re.fullmatch(r"[0-9a-f]{40}", str(runner_provenance.get("workflow_commit", "")))
            or not re.fullmatch(r"[0-9a-f]{64}", str(runner_provenance.get("artifact_sha256", "")))):
            raise PermissionError("CACE independent-reproduction attestation lacks valid OCI run provenance")
    elif runner_provenance is not None:
        raise PermissionError("artifact-integrity attestation must not claim runner reproduction")

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
        "purpose": statement.purpose,
        "runner_provenance": runner_provenance,
        "artifact_count": len(artifact_bytes),
        "artifact_bytes_verified": total_bytes,
        "proof_effect": "none",
        "authority": "verification-only",
    }


def _load_cace_core(cace_app_root: str | Path):
    root = Path(cace_app_root)
    if not (root / "cace_studio" / "core").is_dir():
        raise RuntimeError("CACE core runtime is unavailable at the configured application root")
    import sys
    root_text = str(root.resolve())
    if root_text not in sys.path:
        sys.path.insert(0, root_text)
    try:
        from cace_studio.core.attestation import (
            AttestationStatement,
            generate_ed25519_keypair_pem,
            public_key_id,
            sign_attestation,
        )
        from cace_studio.core.evidence_ledger import bundle_from_payload, verify_bundle
    except ImportError as exc:
        raise RuntimeError("CACE core attestation dependencies are unavailable") from exc
    return AttestationStatement, generate_ed25519_keypair_pem, public_key_id, sign_attestation, bundle_from_payload, verify_bundle


def initialize_merlin_rsi_attestor(
    *, private_key_path: str | Path,
    cace_app_root: str | Path = "/opt/cace-web/current",
) -> dict[str, Any]:
    """Create a CACE signing identity once; never overwrite an existing private key."""
    _, generate_keypair, public_key_id, _, _, _ = _load_cace_core(cace_app_root)
    path = Path(private_key_path)
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    try:
        os.chmod(path.parent, 0o700)
    except OSError:
        pass

    created = False
    if not path.exists():
        private_pem, public_pem = generate_keypair()
        try:
            fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            private_pem = path.read_bytes()
        else:
            with os.fdopen(fd, "wb") as stream:
                stream.write(private_pem)
                stream.flush()
                os.fsync(stream.fileno())
            created = True
    else:
        private_pem = path.read_bytes()

    from cryptography.hazmat.primitives import serialization
    private_key = serialization.load_pem_private_key(private_pem, password=None)
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    return {
        "schema": "cace-merlin-rsi-attestor-identity-v1",
        "created": created,
        "verifier_id": "cace",
        "verifier_key_id": public_key_id(public_pem),
        "public_key_pem": public_pem.decode("ascii"),
        "private_key_path": str(path),
        "private_key_exposed": False,
        "proof_effect": "none",
    }



def _resolve_attestor_private_pem(
    *, private_key_path: str | Path | None, private_key_pem: str | bytes | None,
) -> bytes:
    """Load signer material from an in-memory protected secret or an explicit legacy path."""
    if (private_key_path is None) == (private_key_pem is None):
        raise ValueError("provide exactly one of private_key_path or private_key_pem")
    if private_key_pem is not None:
        if isinstance(private_key_pem, str):
            try:
                raw = private_key_pem.encode("ascii")
            except UnicodeEncodeError as exc:
                raise ValueError("private key PEM must be ASCII") from exc
        elif isinstance(private_key_pem, bytes):
            raw = private_key_pem
        else:
            raise ValueError("private key PEM must be text or bytes")
        if not raw or len(raw) > 64 * 1024 or b"-----BEGIN" not in raw or b"PRIVATE KEY-----" not in raw:
            raise ValueError("private key PEM is empty, oversized, or malformed")
        return raw
    path = Path(private_key_path)
    if not path.is_file() or path.is_symlink():
        raise PermissionError("CACE RSI attestor key is not initialized as a regular file")
    raw = path.read_bytes()
    if not raw or len(raw) > 64 * 1024:
        raise PermissionError("CACE RSI attestor key file is empty or oversized")
    return raw

def attest_merlin_rsi_bundle(
    *,
    bundle_payload: Mapping[str, Any],
    expected_claim_id: str,
    expected_bindings: Mapping[str, Any],
    artifact_bytes_b64: Mapping[str, str],
    private_key_path: str | Path | None = None,
    private_key_pem: str | bytes | None = None,
    cace_app_root: str | Path = "/opt/cace-web/current",
) -> dict[str, Any]:
    """Verify exact EvidenceBundle bytes, then sign an artifact-integrity attestation."""
    AttestationStatement, _, public_key_id, sign_attestation, bundle_from_payload, verify_bundle = _load_cace_core(cace_app_root)
    if not isinstance(expected_claim_id, str) or not expected_claim_id.strip():
        raise ValueError("expected_claim_id must be non-empty")
    if not isinstance(expected_bindings, Mapping):
        raise ValueError("expected_bindings must be an object")
    if not isinstance(artifact_bytes_b64, Mapping):
        raise ValueError("artifact_bytes_b64 must map artifact IDs to base64 bytes")

    bundle = bundle_from_payload(bundle_payload)
    if dict(bundle.bindings) != dict(expected_bindings):
        raise PermissionError("CACE EvidenceBundle bindings do not match the expected RSI evidence")
    if bundle.bindings.get("candidate_id") != expected_claim_id:
        raise PermissionError("CACE EvidenceBundle candidate ID mismatch")
    if len(artifact_bytes_b64) > 32:
        raise ValueError("CACE RSI attestation accepts at most 32 artifacts")
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
        if base64.b64encode(raw).decode("ascii") != encoded:
            raise ValueError("artifact bytes must use canonical base64")
        total_bytes += len(raw)
        if total_bytes > 10 * 1024 * 1024:
            raise ValueError("CACE RSI attestation payload exceeds the 10 MiB limit")
        artifact_bytes[artifact_id] = raw
    try:
        bundle_sha256 = verify_bundle(bundle, artifact_bytes=artifact_bytes)
    except ValueError as exc:
        raise PermissionError(
            "CACE RSI attestor rejected the exact EvidenceBundle artifact bytes"
        ) from exc

    private_pem = _resolve_attestor_private_pem(
        private_key_path=private_key_path, private_key_pem=private_key_pem
    )
    from cryptography.hazmat.primitives import serialization
    private_key = serialization.load_pem_private_key(private_pem, password=None)
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    statement = AttestationStatement(
        verifier_id="cace",
        verifier_key_id=public_key_id(public_pem),
        claim_id=expected_claim_id,
        bundle_sha256=bundle_sha256,
        created_at_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        purpose="artifact-integrity",
        bindings=dict(expected_bindings),
    )
    signed = sign_attestation(statement, private_pem)
    return {
        "schema": "cace-merlin-rsi-attestation-result-v1",
        "attestation": signed.payload(),
        "verified_bundle_sha256": bundle_sha256,
        "artifact_count": len(artifact_bytes),
        "artifact_bytes_verified": total_bytes,
        "verifier_key_id": statement.verifier_key_id,
        "purpose": "artifact-integrity",
        "proof_effect": "none",
        "authority": "verification-only",
    }


def _github_api_json(url: str) -> dict[str, Any]:
    import urllib.request
    if not url.startswith("https://api.github.com/repos/"):
        raise ValueError("CACE reproduction verifier may query only GitHub repository API endpoints")
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "CACE-Merlin-RSI-Verifier",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=12) as response:
            raw = response.read(1_000_001)
    except Exception as exc:
        raise RuntimeError(f"GitHub provenance lookup failed: {type(exc).__name__}") from None
    if len(raw) > 1_000_000:
        raise RuntimeError("GitHub provenance response exceeded 1 MB")
    payload = json.loads(raw.decode("utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError("GitHub provenance response was not an object")
    return payload


def attest_merlin_rsi_reproduction(
    *,
    bundle_payload: Mapping[str, Any],
    expected_claim_id: str,
    expected_bindings: Mapping[str, Any],
    artifact_bytes_b64: Mapping[str, str],
    github_run_id: int,
    trusted_workflow_sha256: str,
    trusted_run_branch: str,
    private_key_path: str | Path | None = None,
    private_key_pem: str | bytes | None = None,
    cace_app_root: str | Path = "/opt/cace-web/current",
    github_fetch=None,
) -> dict[str, Any]:
    """Sign independent-reproduction only after validating the exact successful CACE OCI run."""
    AttestationStatement, _, public_key_id, sign_attestation, bundle_from_payload, verify_bundle = _load_cace_core(cace_app_root)
    if not isinstance(github_run_id, int) or isinstance(github_run_id, bool) or github_run_id <= 0:
        raise ValueError("github_run_id must be a positive integer")
    if not isinstance(expected_bindings, Mapping) or not expected_claim_id:
        raise ValueError("expected claim and bindings are required")
    fetch = github_fetch or _github_api_json
    bundle = bundle_from_payload(bundle_payload)
    if dict(bundle.bindings) != dict(expected_bindings):
        raise PermissionError("CACE EvidenceBundle bindings do not match expected RSI evidence")
    if bundle.bindings.get("candidate_id") != expected_claim_id:
        raise PermissionError("CACE EvidenceBundle candidate ID mismatch")
    if not isinstance(artifact_bytes_b64, Mapping):
        raise ValueError("artifact_bytes_b64 must map artifact IDs to base64 bytes")
    if len(artifact_bytes_b64) > 32:
        raise ValueError("CACE RSI reproduction accepts at most 32 artifacts")
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
        if base64.b64encode(raw).decode("ascii") != encoded:
            raise ValueError("artifact bytes must use canonical base64")
        total_bytes += len(raw)
        if total_bytes > 10 * 1024 * 1024:
            raise ValueError("CACE RSI reproduction payload exceeds the 10 MiB limit")
        artifact_bytes[artifact_id] = raw
    bundle_sha256 = verify_bundle(bundle, artifact_bytes=artifact_bytes)

    api = "https://api.github.com/repos"
    run = fetch(f"{api}/morganaspim/Cace-app/actions/runs/{github_run_id}")
    if (
        not isinstance(trusted_run_branch, str)
        or not trusted_run_branch.strip()
        or trusted_run_branch.startswith("merlin/oci-jobs/")
    ):
        raise PermissionError("CACE signer requires an independently configured protected run branch")
    if (
        run.get("repository", {}).get("full_name") != "morganaspim/Cace-app"
        or run.get("status") != "completed"
        or run.get("conclusion") != "success"
        or run.get("event") != "workflow_dispatch"
        or run.get("head_branch") != trusted_run_branch
    ):
        raise PermissionError("CACE reproduction signing requires a successful manually dispatched run on the configured protected branch")
    run_sha = run.get("head_sha")
    if not isinstance(run_sha, str) or not re.fullmatch(r"[0-9a-f]{40}", run_sha):
        raise PermissionError("CACE OCI run head commit is invalid")
    workflow_path = ".github/workflows/merlin-oci-job-gateway.yml"
    run_path = str(run.get("path", "")).split("@", 1)[0]
    if run_path != workflow_path:
        raise PermissionError("CACE OCI run did not use the approved Merlin job gateway workflow")

    commit = fetch(f"{api}/morganaspim/Cace-app/commits/{run_sha}")
    changed = commit.get("files") or []
    if len(changed) != 1 or changed[0].get("status") not in {"added", "modified"}:
        raise PermissionError("CACE OCI request commit must change exactly one request file")
    request_path = str(changed[0].get("filename", ""))
    if not re.fullmatch(r"merlin/oci-requests/[0-9a-fA-F-]{36}\.json", request_path):
        raise PermissionError("CACE OCI run was not triggered by a valid request file")

    def fetch_file(path: str, repository: str, ref: str) -> bytes:
        from urllib.parse import quote
        item = fetch(f"{api}/{repository}/contents/{quote(path, safe='/')}?ref={ref}")
        if item.get("encoding") != "base64" or not isinstance(item.get("content"), str):
            raise PermissionError("GitHub source file did not return base64 content")
        try:
            return base64.b64decode("".join(item["content"].split()), validate=True)
        except Exception as exc:
            raise PermissionError("GitHub source file content is invalid base64") from exc

    request_doc = json.loads(fetch_file(request_path, "morganaspim/Cace-app", run_sha).decode("utf-8"))
    if (
        request_doc.get("operation") != "merlin_hermes_rsi_full_tests"
        or request_doc.get("source_repo") != expected_bindings.get("source_repo")
        or request_doc.get("source_commit") != expected_bindings.get("source_commit")
    ):
        raise PermissionError("CACE OCI request is not bound to the full Hermes RSI source commit")

    if not isinstance(trusted_workflow_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", trusted_workflow_sha256):
        raise PermissionError("CACE signer requires an independently configured trusted workflow SHA-256")
    workflow_bytes = fetch_file(workflow_path, "morganaspim/Cace-app", run_sha)
    if _sha256(workflow_bytes) != trusted_workflow_sha256:
        raise PermissionError("CACE OCI workflow bytes do not match the independently pinned trusted workflow")
    workflow_text = workflow_bytes.decode("utf-8")
    profile_marker = 'if request["operation"] == "merlin_hermes_rsi_full_tests":'
    if profile_marker not in workflow_text:
        raise PermissionError("CACE OCI workflow omits the fixed Hermes RSI validation profile")
    profile_text = workflow_text.split(profile_marker, 1)[1]
    source_pin = re.search(r'request\["source_commit"\]\s*!=\s*["\']([0-9a-f]{40})["\']', profile_text)
    if not source_pin or source_pin.group(1) != expected_bindings.get("source_commit"):
        raise PermissionError("CACE OCI Hermes RSI profile source pin does not match the candidate source commit")

    if (
        expected_bindings.get("source_repo") != "Mannyspiro/expert-robot"
        or not re.fullmatch(r"[0-9a-f]{40}", str(expected_bindings.get("source_commit", "")))
    ):
        raise PermissionError("CACE reproduction source repository or commit is not allowlisted")

    def git_blob_sha(raw: bytes) -> str:
        return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()

    source_file_paths = (
        "python/merlin/rsi_pipeline.py",
        "python/merlin/rsi.py",
        "python/merlin/event_outbox.py",
        "python/merlin/hermes_rsi_bridge.py",
        "python/merlin/hermes_worker.py",
        "python/merlin/telemetry.py",
        "python/merlin/hermes_outbox.py",
        "python/merlin/runtime_contracts.py",
        "python/merlin/sqlite_registry.py",
        "tests/test_rsi_pipeline.py",
        "tests/test_hermes_rsi_bridge.py",
        "tests/test_hermes_worker.py",
        "tests/test_event_outbox.py",
        "tests/test_hermes_outbox.py",
        "config/benchmarks/merlin_rsi_multidomain_holdout_v1.json",
    )
    source_blob_shas = request_doc.get("source_blob_shas")
    if not isinstance(source_blob_shas, Mapping) or set(source_blob_shas) != set(source_file_paths):
        raise PermissionError("CACE OCI request must pin the complete Hermes RSI source and test set")
    for source_path in source_file_paths:
        expected_blob = source_blob_shas.get(source_path)
        if not isinstance(expected_blob, str) or not re.fullmatch(r"[0-9a-f]{40}", expected_blob):
            raise PermissionError("CACE OCI request lacks a valid source blob pin: " + source_path)
        source_bytes = fetch_file(
            source_path, str(expected_bindings["source_repo"]),
            str(expected_bindings["source_commit"]),
        )
        if git_blob_sha(source_bytes) != expected_blob:
            raise PermissionError("CACE OCI source blob does not match the exact Expert Robot commit: " + source_path)

    benchmark_path = "config/benchmarks/merlin_rsi_multidomain_holdout_v1.json"
    benchmark_bytes = fetch_file(
        benchmark_path, str(expected_bindings["source_repo"]),
        str(expected_bindings["source_commit"]),
    )
    if _sha256(benchmark_bytes) != expected_bindings.get("benchmark_manifest_sha256"):
        raise PermissionError("held-out benchmark manifest digest does not match the source commit")
    benchmark = json.loads(benchmark_bytes.decode("utf-8"))
    if (
        benchmark.get("status") != "frozen"
        or benchmark.get("split") != "held_out"
        or len(benchmark.get("cases", [])) != 25
        or set(benchmark.get("domains", [])) != {"mathematics", "lean", "research", "coding", "engineering"}
    ):
        raise PermissionError("CACE OCI run is not bound to the frozen 25-case multidomain benchmark")

    jobs = fetch(f"{api}/morganaspim/Cace-app/actions/runs/{github_run_id}/jobs?per_page=100")
    matching_jobs = [
        job for job in jobs.get("jobs", [])
        if job.get("name") == "run-approved-profile"
        and job.get("runner_name") == "cace-oci-a1"
        and job.get("conclusion") == "success"
    ]
    if len(matching_jobs) != 1:
        raise PermissionError("CACE OCI run lacks one successful cace-oci-a1 validation job")
    job = matching_jobs[0]
    step_names = {step.get("name"): step.get("conclusion") for step in job.get("steps", [])}
    if (
        step_names.get("Validate request and execute fixed inventory profile") != "success"
        or step_names.get("Upload job receipt and inventory") != "success"
    ):
        raise PermissionError("CACE OCI validation or evidence upload step did not succeed")

    artifacts = fetch(f"{api}/morganaspim/Cace-app/actions/runs/{github_run_id}/artifacts?per_page=100")
    matching_artifacts = [
        artifact for artifact in artifacts.get("artifacts", [])
        if artifact.get("name") == f"merlin-oci-job-{github_run_id}-1"
        and not artifact.get("expired")
        and re.fullmatch(r"sha256:[0-9a-f]{64}", str(artifact.get("digest", "")))
    ]
    if len(matching_artifacts) != 1:
        raise PermissionError("CACE OCI run lacks one retained, SHA-256-bound job receipt artifact")
    artifact = matching_artifacts[0]
    provenance = {
        "schema": "cace-oci-run-provenance-v1",
        "repository": "morganaspim/Cace-app",
        "run_id": github_run_id,
        "workflow_path": workflow_path,
        "workflow_commit": run_sha,
        "runner_name": "cace-oci-a1",
        "job_id": job.get("id"),
        "artifact_sha256": str(artifact["digest"]).removeprefix("sha256:"),
        "source_repo": expected_bindings["source_repo"],
        "source_commit": expected_bindings["source_commit"],
        "benchmark_manifest_sha256": expected_bindings["benchmark_manifest_sha256"],
    }
    signed_bindings = dict(expected_bindings)
    signed_bindings["cace_runner_provenance"] = provenance

    private_pem = _resolve_attestor_private_pem(
        private_key_path=private_key_path, private_key_pem=private_key_pem
    )
    from cryptography.hazmat.primitives import serialization
    private_key = serialization.load_pem_private_key(private_pem, password=None)
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    statement = AttestationStatement(
        verifier_id="cace",
        verifier_key_id=public_key_id(public_pem),
        claim_id=expected_claim_id,
        bundle_sha256=bundle_sha256,
        created_at_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        purpose="independent-reproduction",
        bindings=signed_bindings,
    )
    signed = sign_attestation(statement, private_pem)
    return {
        "schema": "cace-merlin-rsi-reproduction-attestation-v1",
        "attestation": signed.payload(),
        "verified_bundle_sha256": bundle_sha256,
        "artifact_count": len(artifact_bytes),
        "artifact_bytes_verified": total_bytes,
        "verifier_key_id": statement.verifier_key_id,
        "purpose": "independent-reproduction",
        "runner_provenance": provenance,
        "proof_effect": "none",
        "authority": "verification-only",
    }
