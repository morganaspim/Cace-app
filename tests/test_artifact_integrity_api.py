from __future__ import annotations

import base64

import pytest

from cace_studio.core.artifact_integrity_api import (
    ArtifactIntegrityError,
    REQUEST_SCHEMA,
    SOURCE_FILE_KIND,
    create_artifact_integrity_attestation,
)
from cace_studio.core.attestation import (
    attestation_from_payload,
    generate_ed25519_keypair_pem,
    verify_attestation,
)
from cace_studio.core.evidence_ledger import EvidenceArtifact, EvidenceBundle


REPOSITORY = "example/research"
COMMIT = "a" * 40
SOURCE = b"verified source artifact"


def _request(data: bytes = SOURCE) -> dict:
    artifact = EvidenceArtifact.from_bytes(
        "source-artifact",
        data,
        role="source",
        media_type="text/plain",
        path="src/theorem.txt",
    )
    bundle = EvidenceBundle(
        artifacts=(artifact,),
        bindings={
            "source_repository": REPOSITORY,
            "source_commit": COMMIT,
            "artifact_kind": SOURCE_FILE_KIND,
            "tool_version": "test-tool/1.0",
        },
    )
    return {
        "schema": REQUEST_SCHEMA,
        "source_repository": REPOSITORY,
        "source_commit": COMMIT,
        "artifact_kind": SOURCE_FILE_KIND,
        "tool_version": "test-tool/1.0",
        "bundle": bundle.payload(),
        "artifact_bytes_base64": {
            artifact.artifact_id: base64.b64encode(data).decode("ascii")
        },
    }


def _verify(request: dict, private_key: bytes, source_bytes: bytes = SOURCE) -> dict:
    return create_artifact_integrity_attestation(
        request,
        private_key_pem=private_key,
        verifier_id="cace-test-verifier",
        commit_resolver=lambda repository, commit: commit,
        source_file_resolver=lambda repository, commit, path: source_bytes,
        created_at_utc="2026-11-16T12:00:00Z",
    )


def test_exact_source_commit_file_bytes_produce_integrity_only_attestation():
    private_key, _ = generate_ed25519_keypair_pem()
    result = _verify(_request(), private_key)

    attestation = attestation_from_payload(result["attestation"])
    assert verify_attestation(attestation) == result["verifier_key_id"]
    assert attestation.statement.purpose == "artifact-integrity"
    assert result["status"] == "verified"
    assert result["qualification"] is False
    assert result["proof_effect"] == "none"
    assert result["semantic_correctness"] == "not_established"
    assert result["checks"]["exact_commit_source_files_fetched"] is True


def test_rejects_artifact_bytes_that_do_not_match_bundle_digest():
    private_key, _ = generate_ed25519_keypair_pem()
    request = _request(data=b"original")
    request["artifact_bytes_base64"]["source-artifact"] = base64.b64encode(
        b"tampered"
    ).decode("ascii")

    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        _verify(request, private_key, source_bytes=b"original")


def test_rejects_source_file_that_differs_from_exact_commit():
    private_key, _ = generate_ed25519_keypair_pem()
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        _verify(_request(), private_key, source_bytes=b"attacker supplied content")


def test_rejects_commit_resolver_that_does_not_return_exact_commit():
    private_key, _ = generate_ed25519_keypair_pem()
    with pytest.raises(ArtifactIntegrityError, match="exact requested SHA"):
        create_artifact_integrity_attestation(
            _request(),
            private_key_pem=private_key,
            verifier_id="cace-test-verifier",
            commit_resolver=lambda repository, commit: "b" * 40,
            source_file_resolver=lambda repository, commit, path: SOURCE,
        )


def test_rejects_bundle_bound_to_different_repository():
    private_key, _ = generate_ed25519_keypair_pem()
    request = _request()
    request["bundle"]["bindings"]["source_repository"] = "other/repository"

    with pytest.raises(ArtifactIntegrityError, match="source_repository"):
        _verify(request, private_key)


def test_rejects_missing_or_extra_artifact_bytes():
    private_key, _ = generate_ed25519_keypair_pem()
    request = _request()
    request["artifact_bytes_base64"] = {}

    with pytest.raises(ArtifactIntegrityError, match="exactly the bundle artifact IDs"):
        _verify(request, private_key)


def test_rejects_unknown_request_fields():
    private_key, _ = generate_ed25519_keypair_pem()
    request = _request()
    request["trusted"] = True

    with pytest.raises(ArtifactIntegrityError, match="request keys mismatch"):
        _verify(request, private_key)


def test_rejects_generated_artifact_kind_on_source_snapshot_endpoint():
    private_key, _ = generate_ed25519_keypair_pem()
    request = _request()
    request["artifact_kind"] = "generated_build_output"

    with pytest.raises(ArtifactIntegrityError, match="generated outputs need builder provenance"):
        _verify(request, private_key)


def test_rejects_path_traversal_in_bundle_artifact_path():
    private_key, _ = generate_ed25519_keypair_pem()
    request = _request()
    original = EvidenceArtifact.from_bytes(
        "source-artifact", SOURCE, role="source", media_type="text/plain",
        path="../outside.txt",
    )
    bundle = EvidenceBundle(
        artifacts=(original,),
        bindings={
            "source_repository": REPOSITORY,
            "source_commit": COMMIT,
            "artifact_kind": SOURCE_FILE_KIND,
            "tool_version": "test-tool/1.0",
        },
    )
    request["bundle"] = bundle.payload()

    with pytest.raises(ArtifactIntegrityError, match="normalized repository-relative path"):
        _verify(request, private_key)
