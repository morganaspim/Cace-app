from __future__ import annotations

import base64
import hashlib

import pytest

from ops.oci_mcp.merlin_artifact_ref import (
    ARTIFACT_REF_SCHEMA,
    RESPONSE_SCHEMA,
    _exact_ref,
    _expected_bindings,
    resolve_merlin_artifact_bytes,
)


def _fixture():
    raw = b"historical artifact bytes"
    digest = hashlib.sha256(raw).hexdigest()
    ref = {
        "schema": ARTIFACT_REF_SCHEMA,
        "project_id": "project-1",
        "logical_path": "research/result.json",
        "version": 3,
        "sha256": digest,
    }
    response = {
        "schema": RESPONSE_SCHEMA,
        "artifact_ref": ref,
        "resolution": {
            "schema": "merlin-artifact-resolution/1",
            "artifact_ref": ref,
            "verified": True,
            "is_current": False,
            "size_bytes": len(raw),
        },
        "authority": "read_only_artifact_bytes",
        "size_bytes": len(raw),
        "content_sha256": digest,
        "content_b64": base64.b64encode(raw).decode("ascii"),
    }
    return raw, ref, response


def test_resolves_exact_historical_bytes():
    raw, ref, response = _fixture()
    resolved_ref, resolved = resolve_merlin_artifact_bytes(
        ref, resolver=lambda requested: response
    )
    assert resolved_ref == ref
    assert resolved == raw


@pytest.mark.parametrize("field,value", [
    ("project_id", "other-project"),
    ("logical_path", "other/path"),
    ("version", 2),
    ("sha256", "0" * 64),
])
def test_rejects_each_substituted_reference_dimension(field, value):
    _, ref, response = _fixture()
    substituted = dict(ref)
    substituted[field] = value
    with pytest.raises(PermissionError):
        resolve_merlin_artifact_bytes(
            ref, resolver=lambda requested: {**response, "artifact_ref": substituted}
        )


def test_rejects_unverified_historical_resolution():
    _, ref, response = _fixture()
    bad = {**response, "resolution": {**response["resolution"], "verified": False}}
    with pytest.raises(PermissionError):
        resolve_merlin_artifact_bytes(ref, resolver=lambda _: bad)


def test_rejects_noncanonical_base64():
    _, ref, response = _fixture()
    bad = {**response, "content_b64": response["content_b64"].rstrip("=")}
    with pytest.raises(ValueError):
        resolve_merlin_artifact_bytes(ref, resolver=lambda _: bad)


def test_rejects_content_digest_mismatch():
    _, ref, response = _fixture()
    bad = {**response, "content_sha256": "0" * 64}
    with pytest.raises(PermissionError):
        resolve_merlin_artifact_bytes(ref, resolver=lambda _: bad)


def test_rejects_wrong_authority_and_missing_transport():
    _, ref, response = _fixture()
    bad = {**response, "authority": "write"}
    with pytest.raises(PermissionError):
        resolve_merlin_artifact_bytes(ref, resolver=lambda _: bad)
    with pytest.raises(RuntimeError):
        resolve_merlin_artifact_bytes(ref, resolver=None)


def test_exact_reference_rejects_unknown_fields_and_boolean_version():
    _, ref, _ = _fixture()
    with pytest.raises(ValueError):
        _exact_ref({**ref, "extra": "not-bound"})
    with pytest.raises(ValueError):
        _exact_ref({**ref, "version": True})


def test_binding_covers_full_ref_source_and_artifact_identity():
    _, ref, _ = _fixture()
    bindings = _expected_bindings(
        artifact_ref=ref,
        source_repo="Mannyspiro/expert-robot",
        source_commit="a" * 40,
        artifact_id="artifact-123",
        artifact_kind="research-result",
        artifact_schema="research-result/1",
        size_bytes=25,
        content_sha256=ref["sha256"],
    )
    assert bindings["artifact_ref"] == ref
    assert bindings["source_commit"] == "a" * 40
    assert bindings["artifact_id"] == "artifact-123"
    assert bindings["authority"] == "verification-only"
    assert bindings["content_sha256"] == ref["sha256"]


def test_manifest_must_bind_path_role_and_schema():
    from types import SimpleNamespace
    from ops.oci_mcp.merlin_artifact_ref import _artifact_map
    _, ref, _ = _fixture()
    item = SimpleNamespace(
        artifact_id="artifact-123", role="research-result",
        path=ref["logical_path"], metadata={"artifact_schema": "research-result/1"},
        sha256=ref["sha256"],
    )
    bundle = SimpleNamespace(artifacts=(item,))
    assert _artifact_map(
        bundle, artifact_ref=ref, artifact_id="artifact-123",
        artifact_kind="research-result", artifact_schema="research-result/1",
    ) == {"artifact-123": item}
    for field, bad in (
        ("role", "other-kind"),
        ("path", "substituted/path"),
        ("metadata", {"artifact_schema": "other-schema"}),
        ("sha256", "0" * 64),
    ):
        changed = dict(vars(item))
        changed[field] = bad
        altered = SimpleNamespace(**changed)
        with pytest.raises(PermissionError):
            _artifact_map(
                SimpleNamespace(artifacts=(altered,)), artifact_ref=ref,
                artifact_id="artifact-123", artifact_kind="research-result",
                artifact_schema="research-result/1",
            )


def test_manifest_rejects_extra_artifacts():
    from types import SimpleNamespace
    from ops.oci_mcp.merlin_artifact_ref import _artifact_map
    _, ref, _ = _fixture()
    item = SimpleNamespace(
        artifact_id="artifact-123", role="research-result",
        path=ref["logical_path"], metadata={"artifact_schema": "research-result/1"},
        sha256=ref["sha256"],
    )
    with pytest.raises(PermissionError):
        _artifact_map(
            SimpleNamespace(artifacts=(item, item)), artifact_ref=ref,
            artifact_id="artifact-123", artifact_kind="research-result",
            artifact_schema="research-result/1",
        )
