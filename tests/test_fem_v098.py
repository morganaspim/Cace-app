from cace_studio.modules.fem_v098 import *
from cace_studio.core.module import ExecutionContext

def test_v098_capability():
    m=ReliabilityV098()
    p=m.resolved_params({})
    out=m.execute({},p,ExecutionContext(run_id="v098"))
    r=out["result"]
    assert r.get("pass", r.get("pass_", True)) is not False
    assert r["mesh_uniform_theorem"] is False
