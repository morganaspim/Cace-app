from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

SCRIPT = Path(__file__).parents[1] / "scripts" / "generate_v330_proof_dependency_graph.py"
spec = importlib.util.spec_from_file_location("proofdag", SCRIPT)
proofdag = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(proofdag)


def contract():
    return SimpleNamespace(
        claim_id=proofdag.CLAIM_ID,
        contract_id="cace.proof.test.v1",
        contract_sha256="a" * 64,
        endpoint_theorems=("CACEFormal.Test.a", "CACEFormal.Test.b", "CACEFormal.Test.c"),
        allowed_axioms=("Classical.choice", "Quot.sound", "propext"),
        dependency_pins={"mathlib_commit": "5" * 40},
    )


def endpoint(name: str) -> dict:
    return {
        "theorem": name,
        "declaration_kind": "theorem",
        "level_parameters": [],
        "statement_pp_all": f"theorem {name}",
        "statement_sha256": "1" * 64,
        "statement_constants": ["Nat"],
        "binders": [],
        "direct_cace_theorem_dependencies": [],
        "direct_cace_theorem_dependencies_sha256": "2" * 64,
        "transitive_cace_theorem_dependencies": [],
        "transitive_cace_theorem_dependencies_sha256": "3" * 64,
    }


def audit(c, *, axiom: str = "Classical.choice") -> tuple[dict, bytes]:
    value = {
        "schema_version": 1,
        "format": proofdag.AUDIT_FORMAT,
        "audit_source": "CACEFormal/V330AxiomAudit.lean",
        "audit_source_sha256": "4" * 64,
        "theorem_count": len(c.endpoint_theorems),
        "theorems": [{"name": name, "axioms": [axiom]} for name in c.endpoint_theorems],
    }
    data = proofdag.canonical_json_bytes(value)
    return value, data


def environment(c, audit_bytes: bytes) -> tuple[dict, bytes]:
    endpoints = [endpoint(name) for name in c.endpoint_theorems]
    endpoints[0]["binders"] = [
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
            "type_pp_all": "x = x",
            "is_proposition": True,
            "constants": ["Eq"],
        },
    ]
    endpoints[0]["direct_cace_theorem_dependencies"] = [c.endpoint_theorems[1]]
    endpoints[0]["statement_constants"] = ["CACEFormal.Test.Structure", "Nat"]
    value = {
        "artifact_schema": proofdag.ENV_SCHEMA,
        "metadata_state": "LEAN_GENERATED",
        "generator": "CACEFormal.V330TheoremMetadata",
        "provenance": "Lean.Environment",
        "claim_id": c.claim_id,
        "proof_contract_id": c.contract_id,
        "proof_contract_sha256": c.contract_sha256,
        "git_commit": "b" * 40,
        "lean_version": "Lean 4.32.1",
        "lean_toolchain": "leanprover/lean4:v4.32.1",
        "mathlib_commit": c.dependency_pins["mathlib_commit"],
        "kernel_axiom_audit_sha256": proofdag._sha256(audit_bytes),
        "kernel_axiom_audit_theorem_count": len(c.endpoint_theorems),
        "endpoints": endpoints,
        "endpoint_count": len(endpoints),
        "identity_sha256": "6" * 64,
        "proof_effect": "metadata only",
    }
    return value, proofdag.canonical_json_bytes(value)


def make_inputs():
    c = contract()
    audit_value, audit_bytes = audit(c)
    env_value, env_bytes = environment(c, audit_bytes)
    return c, env_value, env_bytes, audit_value, audit_bytes


def build(c, env_value, env_bytes, audit_value, audit_bytes):
    return proofdag.build_graph(
        environment_metadata=env_value,
        environment_metadata_bytes=env_bytes,
        kernel_axiom_audit=audit_value,
        kernel_axiom_audit_bytes=audit_bytes,
        contract=c,
    )


def test_graph_classifies_typed_binders_axioms_and_dependencies():
    c, env_value, env_bytes, audit_value, audit_bytes = make_inputs()
    graph = build(c, env_value, env_bytes, audit_value, audit_bytes)
    nodes = {node["id"]: node for node in graph["nodes"]}
    edges = {(edge["from"], edge["to"], edge["kind"]) for edge in graph["edges"]}

    parameter = f"{c.endpoint_theorems[0]}#binder:0:x"
    assumption = f"{c.endpoint_theorems[0]}#binder:1:h"
    assert nodes[parameter]["classification"] == "parameter"
    assert nodes[assumption]["classification"] == "conditional_open"
    assert nodes["Classical.choice"]["classification"] == "external_allowed_axiom"
    assert nodes["CACEFormal.Test.Structure"]["classification"] == "internal_verified_declaration"
    assert (c.endpoint_theorems[0], c.endpoint_theorems[1], "proof_dependency") in edges
    assert (c.endpoint_theorems[0], assumption, "conditional_binder") in edges
    assert (c.endpoint_theorems[0], parameter, "parameter") in edges
    assert (c.endpoint_theorems[0], "Classical.choice", "axiom_dependency") in edges
    assert "never upgrades qualification" in graph["artifact_role"]


def test_graph_is_deterministic():
    args = make_inputs()
    first = build(*args)
    second = build(*args)
    assert first == second
    assert first["nodes"] == sorted(first["nodes"], key=lambda item: item["id"])
    assert first["edges"] == sorted(first["edges"], key=lambda item: (item["from"], item["to"], item["kind"]))


def test_audit_hash_and_forbidden_axiom_fail_closed():
    c, env_value, env_bytes, audit_value, audit_bytes = make_inputs()
    with pytest.raises(proofdag.ProofDependencyGraphError, match="audit bytes"):
        build(c, env_value, env_bytes, audit_value, audit_bytes + b" ")

    bad_audit, bad_bytes = audit(c, axiom="sorryAx")
    bad_env, bad_env_bytes = environment(c, bad_bytes)
    with pytest.raises(proofdag.ProofDependencyGraphError, match="forbidden|non-whitelisted"):
        build(c, bad_env, bad_env_bytes, bad_audit, bad_bytes)


def test_provenance_endpoint_and_contract_drift_fail_closed():
    c, env_value, env_bytes, audit_value, audit_bytes = make_inputs()
    env_value["proof_contract_sha256"] = "f" * 64
    with pytest.raises(proofdag.ProofDependencyGraphError, match="proof_contract_sha256"):
        build(c, env_value, env_bytes, audit_value, audit_bytes)

    c, env_value, env_bytes, audit_value, audit_bytes = make_inputs()
    env_value["endpoints"].pop()
    env_value["endpoint_count"] -= 1
    with pytest.raises(proofdag.ProofDependencyGraphError, match="endpoint set"):
        build(c, env_value, env_bytes, audit_value, audit_bytes)


def test_endpoint_dependency_cycle_fails_closed():
    c, env_value, env_bytes, audit_value, audit_bytes = make_inputs()
    by_name = {item["theorem"]: item for item in env_value["endpoints"]}
    by_name[c.endpoint_theorems[1]]["direct_cace_theorem_dependencies"] = [c.endpoint_theorems[0]]
    with pytest.raises(proofdag.ProofDependencyGraphError, match="dependency cycle"):
        build(c, env_value, env_bytes, audit_value, audit_bytes)


def test_duplicate_or_missing_audit_record_fails_closed():
    c, env_value, env_bytes, audit_value, audit_bytes = make_inputs()
    audit_value["theorems"].append(dict(audit_value["theorems"][0]))
    rebound_bytes = proofdag.canonical_json_bytes(audit_value)
    env_value["kernel_axiom_audit_sha256"] = proofdag._sha256(rebound_bytes)
    with pytest.raises(proofdag.ProofDependencyGraphError, match="duplicate kernel"):
        build(c, env_value, env_bytes, audit_value, rebound_bytes)

    c, env_value, env_bytes, audit_value, audit_bytes = make_inputs()
    audit_value["theorems"].pop()
    audit_value["theorem_count"] -= 1
    rebound_bytes = proofdag.canonical_json_bytes(audit_value)
    env_value["kernel_axiom_audit_sha256"] = proofdag._sha256(rebound_bytes)
    with pytest.raises(proofdag.ProofDependencyGraphError, match="theorem set"):
        build(c, env_value, env_bytes, audit_value, rebound_bytes)
