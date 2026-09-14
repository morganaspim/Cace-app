import os, tempfile
from pathlib import Path
from cace_studio.modules.formal_v321 import FormalV321, mesh_admissibility_to_orthogonality, mesh_orthogonality_artifact
from cace_studio.core.mesh_orthogonality_bridge import invoke_mesh_orthogonality_checker
from cace_studio.core.module import ExecutionContext

def test_v321_mesh_admissibility_derives_orthogonality():
    r=mesh_admissibility_to_orthogonality()
    assert r["pass"] is True
    assert r["exact_checker"]["passed"] is True
    assert r["exact_checker"]["global_pairing"] == "0"
    assert r["orthogonality_derived_not_assumed"] is True
    assert r["negative_tests"]["nonzero_boundary_rejected"] is True
    assert r["negative_tests"]["normal_discontinuity_rejected"] is True

def test_v321_checker_is_cwd_independent():
    here=os.getcwd()
    with tempfile.TemporaryDirectory() as td:
        os.chdir(td)
        try:
            r=invoke_mesh_orthogonality_checker(mesh_orthogonality_artifact())
        finally:
            os.chdir(here)
    assert r["passed"] is True
    assert r["cwd_independent"] is True

def test_v321_module():
    m=FormalV321()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v321"))
    assert out["result"]["pass"] is True
