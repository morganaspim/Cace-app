import os
import tempfile

from cace_studio.core.mesh_orthogonality_bridge import invoke_mesh_orthogonality_checker
from cace_studio.core.module import ExecutionContext
from cace_studio.modules.formal_v322 import (
    FormalV322,
    concrete_mesh_certificate_artifact,
    concrete_mesh_certificate_to_prager_synge,
)


def test_v322_concrete_mesh_certificate_to_prager_synge():
    r = concrete_mesh_certificate_to_prager_synge()
    assert r["pass"] is True
    assert r["exact_checker"]["passed"] is True
    assert r["exact_checker"]["global_pairing"] == "0"
    assert r["orthogonality_derived_not_assumed"] is True
    assert r["lean_concrete_mesh_certificate_closed"] is True
    assert r["negative_tests"]["nonzero_boundary_rejected"] is True
    assert r["negative_tests"]["normal_discontinuity_rejected"] is True
    assert "CACEFormal.v322_discrete_prager_synge_from_concrete_mesh" in r["lean_theorems"]


def test_v322_checker_is_cwd_independent():
    here = os.getcwd()
    with tempfile.TemporaryDirectory() as td:
        os.chdir(td)
        try:
            r = invoke_mesh_orthogonality_checker(concrete_mesh_certificate_artifact())
        finally:
            os.chdir(here)
    assert r["passed"] is True
    assert r["cwd_independent"] is True


def test_v322_module():
    m = FormalV322()
    out = m.execute({}, m.resolved_params({}), ExecutionContext(run_id="v322"))
    assert out["result"]["pass"] is True
