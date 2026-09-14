
from cace_studio.modules.fem_v101 import (
    executable_closure_audit, hypothesis_matcher, derive_face_estimate_symbolically,
    reliability_constant_formula, closure_dag, ReliabilityClosureV101, reviewed_reliability_contract
)
from cace_studio.core.module import ExecutionContext

def test_v101_default_closure_is_reviewed_not_formal():
    r = executable_closure_audit()
    assert r["pass"]
    assert r["reviewed_theorem_available"] is True
    assert r["formal_theorem_available"] is False
    assert r["reliability_theorem"]["status"] == "reviewed-assumed"
    assert r["reliability_theorem"]["machine_checked"] is False

def test_v101_missing_jump_term_refuses_theorem_match():
    facts = {
        "bounded_polyhedral_lipschitz_domain": True,
        "conforming_affine_simplicial_family": True,
        "uniform_shape_regularity": True,
        "P1_space": True,
        "homogeneous_dirichlet": True,
        "alpha_lower": 1.0,
        "volume_residual_term": True,
        "jump_term": False,
    }
    r = hypothesis_matcher(facts)
    assert not r["pass"]
    assert "residual_estimator_has_jump_term" in r["failed"]

def test_v101_face_estimate_is_derived_but_not_machine_checked():
    r = derive_face_estimate_symbolically()
    assert r["pass"]
    assert "C_tr" in r["derived_constant"]
    assert r["machine_checked"] is False

def test_v101_reliability_constant_is_mesh_size_independent():
    r = reliability_constant_formula()
    assert r["pass"]
    assert "mesh size h" in r["independent_of"]
    assert "sqrt(alpha)" in r["C_rel"]

def test_v101_dag_closes_reviewed_only():
    r = closure_dag()
    assert r["reviewed_reliability_promotable"] is True
    assert r["formal_reliability_promotable"] is False
    assert r["nodes"]["mesh_uniform_patch_overlap"] == "closed-reviewed-import"

def test_v101_module_executes():
    m = ReliabilityClosureV101()
    out = m.execute({}, m.resolved_params({}), ExecutionContext(run_id="v101"))
    assert out["result"]["pass"]


def test_v101_reviewed_theorem_contract_matches_and_refuses():
    c = reviewed_reliability_contract()
    good = {
        "bounded_polyhedral_lipschitz_domain": True,
        "conforming_affine_simplicial_family": True,
        "uniform_shape_regularity": True,
        "P1_space": True,
        "homogeneous_dirichlet": True,
        "alpha_lower": 0.25,
        "volume_residual_term": True,
        "jump_term": True,
    }
    ok, misses = c.match(good)
    assert ok and not misses
    bad = dict(good); bad["uniform_shape_regularity"] = False
    ok, misses = c.match(bad)
    assert not ok
    assert "uniform_shape_regularity" in misses
    assert c.status.value == "reviewed-assumed"
