from __future__ import annotations

from copy import deepcopy
import importlib.util
import json
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parents[1] / "scripts" / "export_v330_environment_metadata.py"
spec = importlib.util.spec_from_file_location("envmeta", SCRIPT)
envmeta = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(envmeta)


def record(name: str = "CACEFormal.Test.endpoint") -> dict:
    return {
        "schema": envmeta.RECORD_SCHEMA,
        "generator": envmeta.GENERATOR,
        "theorem": name,
        "declaration_kind": "theorem",
        "level_parameters": [],
        "statement_pp_all": "∀ (x : Nat), x = x",
        "statement_constants": ["Nat"],
        "direct_cace_theorem_dependencies": ["CACEFormal.Test.helper"],
        "transitive_cace_theorem_dependencies": ["CACEFormal.Test.helper"],
    }


def raw(*records: dict) -> str:
    return "\n".join(
        envmeta.SENTINEL + json.dumps(item, sort_keys=True, separators=(",", ":"))
        for item in records
    )


def artifact(item: dict | None = None, **overrides) -> dict:
    kwargs = {
        "raw_output": raw(item or record()),
        "expected_endpoints": ["CACEFormal.Test.endpoint"],
        "lean_version": "Lean 4.32.1",
        "lean_toolchain": "leanprover/lean4:v4.32.1",
        "mathlib_commit": "5" * 40,
        "claim_id": "cace.test.claim",
        "proof_contract_id": "cace.proof.test.v1",
        "proof_contract_sha256": "a" * 64,
        "git_commit": "b" * 40,
    }
    kwargs.update(overrides)
    return envmeta.build_artifact(**kwargs)


def test_missing_sentinel_fails_closed():
    with pytest.raises(envmeta.EnvironmentMetadataError, match="sentinel"):
        envmeta.parse_records("{}")


def test_endpoint_drift_fails_closed():
    with pytest.raises(envmeta.EnvironmentMetadataError, match="endpoint set differs"):
        envmeta.validate_records(
            envmeta.parse_records(raw(record())),
            expected_endpoints=["CACEFormal.Test.other"],
        )


def test_dependency_closure_must_cover_direct_edges():
    item = record()
    item["transitive_cace_theorem_dependencies"] = []
    with pytest.raises(envmeta.EnvironmentMetadataError, match="omits direct"):
        envmeta.validate_records(
            envmeta.parse_records(raw(item)),
            expected_endpoints=[item["theorem"]],
        )


def test_generator_spoof_fails_closed():
    item = record()
    item["generator"] = "text-parser"
    with pytest.raises(envmeta.EnvironmentMetadataError, match="unexpected Lean generator"):
        envmeta.validate_records(
            envmeta.parse_records(raw(item)),
            expected_endpoints=[item["theorem"]],
        )


def test_extra_fields_fail_closed():
    item = record()
    item["invented"] = True
    with pytest.raises(envmeta.EnvironmentMetadataError, match="record keys mismatch"):
        envmeta.validate_records(
            envmeta.parse_records(raw(item)),
            expected_endpoints=[item["theorem"]],
        )


def test_artifact_is_deterministic_statement_contract_and_commit_bound():
    first = artifact()
    second = artifact()
    assert first == second
    assert first["artifact_schema"] == "cace-lean-theorem-metadata-v2"
    assert first["metadata_state"] == "LEAN_GENERATED"
    assert first["provenance"] == "Lean.Environment"
    assert first["proof_contract_id"] == "cace.proof.test.v1"
    assert first["proof_contract_sha256"] == "a" * 64
    assert first["git_commit"] == "b" * 40
    assert "does not independently qualify" in first["proof_effect"]

    changed = record()
    changed["statement_pp_all"] = "∀ (x : Nat), x + 0 = x"
    statement_changed = artifact(changed)
    assert statement_changed["identity_sha256"] != first["identity_sha256"]
    assert (
        statement_changed["endpoints"][0]["statement_sha256"]
        != first["endpoints"][0]["statement_sha256"]
    )

    contract_changed = artifact(proof_contract_sha256="c" * 64)
    assert contract_changed["identity_sha256"] != first["identity_sha256"]

    commit_changed = artifact(git_commit="d" * 40)
    assert commit_changed["identity_sha256"] != first["identity_sha256"]


def test_malformed_binding_identities_fail_closed():
    with pytest.raises(envmeta.EnvironmentMetadataError, match="proof_contract_sha256"):
        artifact(proof_contract_sha256="not-a-hash")
    with pytest.raises(envmeta.EnvironmentMetadataError, match="git_commit"):
        artifact(git_commit="1234")
    with pytest.raises(envmeta.EnvironmentMetadataError, match="claim_id"):
        artifact(claim_id="")
