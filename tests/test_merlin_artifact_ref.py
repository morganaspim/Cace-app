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
            "provenance": {
                "schema": "merlin-artifact-provenance/1",
                "source_repo": "Mannyspiro/expert-robot",
                "source_commit": "a" * 40,
                "artifact_id": "artifact-123",
                "artifact_kind": "research-result",
                "artifact_schema": "research-result/1",
            },
        },
        "authority": "read_only_artifact_bytes",
        "size_bytes": len(raw),
        "content_sha256": digest,
        "content_b64": base64.b64encode(raw).decode("ascii"),
    }
    return raw, ref, response


def test_resolves_exact_historical_bytes():
    raw, ref, response = _fixture()
    resolved_ref, resolved, provenance = resolve_merlin_artifact_bytes(
        ref, resolver=lambda requested: response
    )
    assert resolved_ref == ref
    assert resolved == raw
    assert provenance["source_commit"] == "a" * 40


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


def test_full_attestation_round_trip_and_pinned_trust(tmp_path):
    pytest.importorskip("cryptography")
    import json
    from cace_studio.core.attestation import generate_ed25519_keypair_pem, public_key_id
    from cace_studio.core.evidence_ledger import EvidenceArtifact, EvidenceBundle
    from ops.oci_mcp.merlin_artifact_ref import (
        _expected_bindings, attest_merlin_artifact_ref, verify_merlin_artifact_ref,
    )

    raw, ref, response = _fixture()
    source_commit = "a" * 40
    artifact_id = "artifact-123"
    artifact_kind = "research-result"
    artifact_schema = "research-result/1"
    bindings = _expected_bindings(
        artifact_ref=ref, source_repo="Mannyspiro/expert-robot",
        source_commit=source_commit, artifact_id=artifact_id,
        artifact_kind=artifact_kind, artifact_schema=artifact_schema,
        size_bytes=len(raw), content_sha256=ref["sha256"],
    )
    artifact = EvidenceArtifact.from_bytes(
        artifact_id, raw, role=artifact_kind, path=ref["logical_path"],
        metadata={"artifact_schema": artifact_schema},
    )
    bundle = EvidenceBundle(artifacts=(artifact,), bindings=bindings)
    private_pem, public_pem = generate_ed25519_keypair_pem()
    resolver = lambda requested: response

    signed = attest_merlin_artifact_ref(
        bundle_payload=bundle.payload(), artifact_ref=ref,
        source_repo="Mannyspiro/expert-robot", source_commit=source_commit,
        artifact_id=artifact_id, artifact_kind=artifact_kind,
        artifact_schema=artifact_schema, resolver=resolver,
        private_key_pem=private_pem, cace_app_root=".",
    )
    trust = {
        "schema": "merlin-cace-trust-store-v1",
        "keys": [{
            "key_id": public_key_id(public_pem),
            "verifier_id": "cace", "status": "active",
        }],
    }
    trust_json = json.dumps(trust, sort_keys=True, separators=(",", ":"))
    result = verify_merlin_artifact_ref(
        bundle_payload=bundle.payload(), attestation_payload=signed["attestation"],
        artifact_ref=ref, source_repo="Mannyspiro/expert-robot",
        source_commit=source_commit, artifact_id=artifact_id,
        artifact_kind=artifact_kind, artifact_schema=artifact_schema,
        resolver=resolver, trust_store_json=trust_json,
        trust_store_sha256=hashlib.sha256(trust_json.encode()).hexdigest(),
        cace_app_root=".",
    )
    assert result["verified"] is True
    assert result["proof_effect"] == "none"
    assert result["authority"] == "verification-only"

    with pytest.raises(PermissionError):
        verify_merlin_artifact_ref(
            bundle_payload=bundle.payload(), attestation_payload=signed["attestation"],
            artifact_ref=ref, source_repo="Mannyspiro/expert-robot",
            source_commit="b" * 40, artifact_id=artifact_id,
            artifact_kind=artifact_kind, artifact_schema=artifact_schema,
            resolver=resolver, trust_store_json=trust_json,
            trust_store_sha256=hashlib.sha256(trust_json.encode()).hexdigest(),
            cace_app_root=".",
        )


def test_trust_store_rejects_duplicate_keys_and_digest_mismatch():
    import json
    from ops.oci_mcp.merlin_artifact_ref import _approved_artifact_ref_keys
    entry = {
        "key_id": "ed25519:" + "a" * 64,
        "verifier_id": "cace", "status": "active",
    }
    trust = {"schema": "merlin-cace-trust-store-v1", "keys": [entry, entry]}
    encoded = json.dumps(trust, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(encoded.encode()).hexdigest()
    with pytest.raises(PermissionError):
        _approved_artifact_ref_keys(encoded, digest)
    with pytest.raises(PermissionError):
        _approved_artifact_ref_keys(encoded, "0" * 64)


def test_mcp_server_is_initialized_before_tool_registration():
    import ast
    from pathlib import Path
    source = Path(__file__).parents[1] / "ops" / "oci_mcp" / "server.py"
    tree = ast.parse(source.read_text(encoding="utf-8"))
    server_line = None
    tool_lines = []
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "mcp"
            for target in node.targets
        ) and isinstance(node.value, ast.Call) and getattr(node.value.func, "id", None) == "MCPServer":
            server_line = node.lineno
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for decorator in node.decorator_list:
                if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute):
                    if isinstance(decorator.func.value, ast.Name) and decorator.func.value.id == "mcp":
                        tool_lines.append(node.lineno)
    assert server_line is not None
    assert tool_lines
    assert server_line < min(tool_lines)

@pytest.mark.parametrize("change", [
    {"schema": "merlin-artifact-resolution/0"},
    {"verified": False},
    {"is_current": 1},
    {"size_bytes": True},
])
def test_rejects_noncanonical_historical_resolution_metadata(change):
    _, ref, response = _fixture()
    bad = {**response, "resolution": {**response["resolution"], **change}}
    with pytest.raises(PermissionError):
        resolve_merlin_artifact_bytes(ref, resolver=lambda _: bad)


def test_rejects_nested_reference_substitution():
    _, ref, response = _fixture()
    nested = dict(response["resolution"]["artifact_ref"])
    nested["project_id"] = "different-project"
    bad = {
        **response,
        "resolution": {**response["resolution"], "artifact_ref": nested},
    }
    with pytest.raises(PermissionError):
        resolve_merlin_artifact_bytes(ref, resolver=lambda _: bad)


def test_resolver_provenance_is_mandatory_and_exact():
    _, ref, response = _fixture()
    missing = {**response, "resolution": {
        key: value for key, value in response["resolution"].items() if key != "provenance"
    }}
    with pytest.raises(PermissionError):
        resolve_merlin_artifact_bytes(ref, resolver=lambda _: missing)
    substituted = {**response, "resolution": {
        **response["resolution"],
        "provenance": {
            **response["resolution"]["provenance"],
            "source_commit": "b" * 40,
        },
    }}
    _, _, provenance = resolve_merlin_artifact_bytes(ref, resolver=lambda _: substituted)
    assert provenance["source_commit"] == "b" * 40
