from __future__ import annotations

import base64

import pytest

from cace_studio.core.artifact_integrity_api import (
    ArtifactIntegrityError,
    REQUEST_SCHEMA,
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


def _request(data: bytes = b"verified source artifact") -> dict:
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
            "artifact_kind": "source_snapshot",
            "tool_version": "test-tool/1.0",
        },
    )
    return {
        "schema": REQUEST_SCHEMA,
        "source_repository": REPOSITORY,
        "source_commit": COMMIT,
        "artifact_kind": "source_snapshot",
        "tool_version": "test-tool/1.0",
        "bundle": bundle.payload(),
        "artifact_bytes_base64": {
            artifact.artifact_id: base64.b64encode(data).decode("ascii")
        },
    }


def test_exact_source_and_artifact_bytes_produce_integrity_only_attestation():
    private_key, _ = generate_ed25519_keypair_pem()
    result = create_artifact_integrity_attestation(
        _request(),
        private_key_pem=private_key,
        verifier_id="cace-test-verifier",
        commit_resolver=lambda repository, commit: commit,
        created_at_utc="2026-11-16T12:00:00Z",
    )

    attestation = attestation_from_payload(result["attestation"])
    assert verify_attestation(attestation) == result["verifier_key_id"]
    assert attestation.statement.purpose == "artifact-integrity"
    assert result["status"] == "verified"
    assert result["qualification"] is False
    assert result["proof_effect"] == "none"
    assert result["semantic_correctness"] == "not_established"
    assert result["checks"]["github_commit_exact_match"] is True


def test_rejects_artifact_bytes_that_do_not_match_bundle_digest():
    private_key, _ = generate_ed25519_keypair_pem()
    request = _request(data=b"original")
    request["artifact_bytes_base64"]["source-artifact"] = base64.b64encode(
        b"tampered"
    ).decode("ascii")

    with pytest.raises(ValueError, match="size mismatch|SHA-256 mismatch"):
        create_artifact_integrity_attestation(
            request,
            private_key_pem=private_key,
            verifier_id="cace-test-verifier",
            commit_resolver=lambda repository, commit: commit,
        )


def test_rejects_commit_resolver_that_does_not_return_exact_commit():
    private_key, _ = generate_ed25519_keypair_pem()
    with pytest.raises(ArtifactIntegrityError, match="exact requested SHA"):
        create_artifact_integrity_attestation(
            _request(),
            private_key_pem=private_key,
            verifier_id="cace-test-verifier",
            commit_resolver=lambda repository, commit: "b" * 40,
        )


def test_rejects_bundle_bound_to_different_repository():
    private_key, _ = generate_ed25519_keypair_pem()
    request = _request()
    request["bundle"]["bindings"]["source_repository"] = "other/repository"

    with pytest.raises(ArtifactIntegrityError, match="source_repository"):
        create_artifact_integrity_attestation(
            request,
            private_key_pem=private_key,
            verifier_id="cace-test-verifier",
            commit_resolver=lambda repository, commit: commit,
        )


def test_rejects_missing_or_extra_artifact_bytes():
    private_key, _ = generate_ed25519_keypair_pem()
    request = _request()
    request["artifact_bytes_base64"] = {}

    with pytest.raises(ArtifactIntegrityError, match="exactly the bundle artifact IDs"):
        create_artifact_integrity_attestation(
            request,
            private_key_pem=private_key,
            verifier_id="cace-test-verifier",
            commit_resolver=lambda repository, commit: commit,
        )


def test_rejects_unknown_request_fields():
    private_key, _ = generate_ed25519_keypair_pem()
    request = _request()
    request["trusted"] = True

    with pytest.raises(ArtifactIntegrityError, match="request keys mismatch"):
        create_artifact_integrity_attestation(
            request,
            private_key_pem=private_key,
            verifier_id="cace-test-verifier",
            commit_resolver=lambda repository, commit: commit,
        )
