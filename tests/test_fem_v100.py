from cace_studio.modules.fem_v100 import *
from cace_studio.core.module import ExecutionContext

def test_v100_capability():
    m=ReliabilityV100()
    p=m.resolved_params({})
    out=m.execute({},p,ExecutionContext(run_id="v100"))
    r=out["result"]
    assert r.get("pass", r.get("pass_", True)) is not False
    assert r["reliability_theorem_formally_verified"] is False
    assert "trace_local" in r["blocking_nodes"]
