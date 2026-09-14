from cace_studio.modules.fem_v099 import *
from cace_studio.core.module import ExecutionContext

def test_v099_capability():
    m=ReliabilityV099()
    p=m.resolved_params({})
    out=m.execute({},p,ExecutionContext(run_id="v099"))
    r=out["result"]
    assert r.get("pass", r.get("pass_", True)) is not False
    assert r["reliability_promotable"] is False
