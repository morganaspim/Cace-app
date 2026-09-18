from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts" / "export_v330_environment_metadata.py"
spec = importlib.util.spec_from_file_location("envmeta", SCRIPT)
envmeta = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(envmeta)

DAG_SCRIPT = ROOT / "scripts" / "generate_v330_proof_dependency_graph.py"
dag_spec = importlib.util.spec_from_file_location("proofdag", DAG_SCRIPT)
proofdag = importlib.util.module_from_spec(dag_spec)
assert dag_spec.loader is not None
dag_spec.loader.exec_module(proofdag)


def record(name: str = "CACEFormal.Test.endpoint") -> dict:
    return {
        "schema": envmeta.RECORD_SCHEMA,
        "generator": envmeta.GENERATOR,
        "theorem": name,
        "declaration_kind": "theorem",
        "level_parameters": [],
        "statement_pp_all": "∀ (x : Nat) (h : x = x), x = x",
        "statement_constants": ["Eq", "Nat"],
        "binders": [
            {
                "index": 0,
                "name": "x",
                "binder_info": "explicit",
                "type_pp_all": "Nat",
                "is_proposition": False,
                "constants": ["Nat"],
            },
            {
                "index": 1,
                "name": "h",
                "binder_info": "explicit",
                "type_pp_all": "Eq Nat x x",
                "is_proposition": True,
                "constants": ["Eq", "Nat"],
            },
        ],
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
        "kernel_axiom_audit_sha256": "e" * 64,
        "kernel_axiom_audit_theorem_count": 1,
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


def test_binder_schema_is_typed_ordered_and_fail_closed():
    normalized = envmeta.validate_records(
        envmeta.parse_records(raw(record())),
        expected_endpoints=["CACEFormal.Test.endpoint"],
    )[0]
    assert normalized["binders"][0]["is_proposition"] is False
    assert normalized["binders"][1]["is_proposition"] is True

    bad_index = record()
    bad_index["binders"][1]["index"] = 3
    with pytest.raises(envmeta.EnvironmentMetadataError, match="index must equal 1"):
        envmeta.validate_records(
            envmeta.parse_records(raw(bad_index)), expected_endpoints=[bad_index["theorem"]]
        )

    old_schema = record()
    old_schema["schema"] = "cace-lean-theorem-record-v1"
    with pytest.raises(envmeta.EnvironmentMetadataError, match="unsupported record schema"):
        envmeta.validate_records(
            envmeta.parse_records(raw(old_schema)), expected_endpoints=[old_schema["theorem"]]
        )

    bad_prop = record()
    bad_prop["binders"][1]["is_proposition"] = "true"
    with pytest.raises(envmeta.EnvironmentMetadataError, match="must be boolean"):
        envmeta.validate_records(
            envmeta.parse_records(raw(bad_prop)), expected_endpoints=[bad_prop["theorem"]]
        )


def test_artifact_is_deterministic_statement_contract_commit_audit_and_binder_bound():
    first = artifact()
    second = artifact()
    assert first == second
    assert first["artifact_schema"] == "cace-lean-theorem-metadata-v3"
    assert first["metadata_state"] == "LEAN_GENERATED"
    assert first["provenance"] == "Lean.Environment"
    assert first["proof_contract_id"] == "cace.proof.test.v1"
    assert first["proof_contract_sha256"] == "a" * 64
    assert first["git_commit"] == "b" * 40
    assert first["kernel_axiom_audit_sha256"] == "e" * 64
    assert first["kernel_axiom_audit_theorem_count"] == 1
    assert "does not independently qualify" in first["proof_effect"]

    changed = record()
    changed["statement_pp_all"] = "∀ (x : Nat), x + 0 = x"
    assert artifact(changed)["identity_sha256"] != first["identity_sha256"]

    binder_changed = record()
    binder_changed["binders"][1]["name"] = "proof"
    assert artifact(binder_changed)["identity_sha256"] != first["identity_sha256"]

    assert artifact(proof_contract_sha256="c" * 64)["identity_sha256"] != first["identity_sha256"]
    assert artifact(git_commit="d" * 40)["identity_sha256"] != first["identity_sha256"]
    assert artifact(kernel_axiom_audit_sha256="f" * 64)["identity_sha256"] != first["identity_sha256"]


def test_malformed_binding_identities_and_audit_count_fail_closed():
    with pytest.raises(envmeta.EnvironmentMetadataError, match="proof_contract_sha256"):
        artifact(proof_contract_sha256="not-a-hash")
    with pytest.raises(envmeta.EnvironmentMetadataError, match="git_commit"):
        artifact(git_commit="1234")
    with pytest.raises(envmeta.EnvironmentMetadataError, match="kernel_axiom_audit_sha256"):
        artifact(kernel_axiom_audit_sha256="bad")
    with pytest.raises(envmeta.EnvironmentMetadataError, match="theorem count"):
        artifact(kernel_axiom_audit_theorem_count=2)
    with pytest.raises(envmeta.EnvironmentMetadataError, match="claim_id"):
        artifact(claim_id="")


def _rank5_contract():
    return SimpleNamespace(
        claim_id=proofdag.CLAIM_ID,
        contract_id="cace.proof.test.v1",
        contract_sha256="a" * 64,
        endpoint_theorems=("CACEFormal.Test.a", "CACEFormal.Test.b"),
        allowed_axioms=("Classical.choice", "Quot.sound", "propext"),
        dependency_pins={"mathlib_commit": "5" * 40},
    )


def _rank5_evidence(c):
    audit_value = {
        "schema_version": 1,
        "format": proofdag.AUDIT_FORMAT,
        "audit_source": "CACEFormal/V330AxiomAudit.lean",
        "audit_source_sha256": "4" * 64,
        "theorem_count": 2,
        "theorems": [
            {"name": c.endpoint_theorems[0], "axioms": ["Classical.choice"]},
            {"name": c.endpoint_theorems[1], "axioms": ["propext"]},
        ],
    }
    audit_bytes = proofdag.canonical_json_bytes(audit_value)
    first = {
        "theorem": c.endpoint_theorems[0],
        "statement_constants": ["CACEFormal.Test.Structure", "Nat"],
        "binders": [
            {"index": 0, "name": "x", "binder_info": "explicit", "type_pp_all": "Nat", "is_proposition": False, "constants": ["Nat"]},
            {"index": 1, "name": "h", "binder_info": "explicit", "type_pp_all": "x = x", "is_proposition": True, "constants": ["Eq"]},
        ],
        "direct_cace_theorem_dependencies": [c.endpoint_theorems[1]],
    }
    second = {
        "theorem": c.endpoint_theorems[1],
        "statement_constants": ["Nat"],
        "binders": [],
        "direct_cace_theorem_dependencies": [],
    }
    env_value = {
        "artifact_schema": proofdag.ENV_SCHEMA,
        "metadata_state": "LEAN_GENERATED",
        "provenance": "Lean.Environment",
        "claim_id": c.claim_id,
        "proof_contract_id": c.contract_id,
        "proof_contract_sha256": c.contract_sha256,
        "git_commit": "b" * 40,
        "lean_version": "Lean 4.32.1",
        "lean_toolchain": "leanprover/lean4:v4.32.1",
        "mathlib_commit": c.dependency_pins["mathlib_commit"],
        "kernel_axiom_audit_sha256": proofdag._sha256(audit_bytes),
        "kernel_axiom_audit_theorem_count": 2,
        "endpoints": [first, second],
        "endpoint_count": 2,
    }
    return env_value, proofdag.canonical_json_bytes(env_value), audit_value, audit_bytes


def test_rank5_proof_dag_smoke_classifies_kernel_derived_assumptions():
    c = _rank5_contract()
    env_value, env_bytes, audit_value, audit_bytes = _rank5_evidence(c)
    graph = proofdag.build_graph(
        environment_metadata=env_value,
        environment_metadata_bytes=env_bytes,
        kernel_axiom_audit=audit_value,
        kernel_axiom_audit_bytes=audit_bytes,
        contract=c,
    )
    nodes = {node["id"]: node for node in graph["nodes"]}
    assert nodes[f"{c.endpoint_theorems[0]}#binder:0:x"]["classification"] == "parameter"
    assert nodes[f"{c.endpoint_theorems[0]}#binder:1:h"]["classification"] == "conditional_open"
    assert nodes["Classical.choice"]["classification"] == "external_allowed_axiom"
    assert nodes["CACEFormal.Test.Structure"]["classification"] == "internal_verified_declaration"


def test_rank5_proof_dag_cycle_and_axiom_escape_fail_closed():
    c = _rank5_contract()
    env_value, env_bytes, audit_value, audit_bytes = _rank5_evidence(c)
    env_value["endpoints"][1]["direct_cace_theorem_dependencies"] = [c.endpoint_theorems[0]]
    with pytest.raises(proofdag.ProofDependencyGraphError, match="dependency cycle"):
        proofdag.build_graph(
            environment_metadata=env_value,
            environment_metadata_bytes=env_bytes,
            kernel_axiom_audit=audit_value,
            kernel_axiom_audit_bytes=audit_bytes,
            contract=c,
        )

    env_value, env_bytes, audit_value, _ = _rank5_evidence(c)
    audit_value["theorems"][0]["axioms"] = ["sorryAx"]
    bad_audit_bytes = proofdag.canonical_json_bytes(audit_value)
    env_value["kernel_axiom_audit_sha256"] = proofdag._sha256(bad_audit_bytes)
    with pytest.raises(proofdag.ProofDependencyGraphError, match="forbidden|non-whitelisted"):
        proofdag.build_graph(
            environment_metadata=env_value,
            environment_metadata_bytes=env_bytes,
            kernel_axiom_audit=audit_value,
            kernel_axiom_audit_bytes=bad_audit_bytes,
            contract=c,
        )


def test_rank5_lean_exporter_compiles_on_cached_oci_runner(tmp_path: Path):
    """Compile the Meta exporter on the self-hosted OCI gate without burdening local tests."""
    elan_home = Path("/var/lib/cace-cache/elan")
    package_cache = Path(
        "/var/lib/cace-cache/mathlib/v4.32.1-520045ab14e26149ee970e2e617ca04b09bde5d6/packages"
    )
    lake = elan_home / "bin/lake"
    if not lake.is_file() or not (package_cache / "mathlib/.git").is_dir():
        pytest.skip("pinned OCI Lean cache is not available")

    formal = tmp_path / "formal"
    shutil.copytree(
        ROOT / "formal/cace_formal",
        formal,
        ignore=shutil.ignore_patterns(".lake"),
    )
    (formal / ".lake").mkdir()
    os.symlink(package_cache, formal / ".lake/packages", target_is_directory=True)
    env = os.environ.copy()
    env["ELAN_HOME"] = str(elan_home)

    subprocess.run(
        [str(lake), "build", "CACEFormal.V330AxiomAudit"],
        cwd=formal,
        env=env,
        check=True,
        text=True,
    )
    completed = subprocess.run(
        [str(lake), "env", "lean", "CACEFormal/V330TheoremMetadata.lean"],
        cwd=formal,
        env=env,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    records = envmeta.parse_records(completed.stdout)
    assert records
    assert all(item["schema"] == "cace-lean-theorem-record-v2" for item in records)
    assert all("binders" in item for item in records)
