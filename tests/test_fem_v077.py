from cace_studio.modules.fem_v077 import *
from cace_studio.core.module import ExecutionContext

def test_v077_capability():
    m=ReliabilityV077()
    p=m.resolved_params({})
    out=m.execute({},p,ExecutionContext(run_id="v077"))
    r=out["result"]
    assert r.get("pass", r.get("pass_", True)) is not False
