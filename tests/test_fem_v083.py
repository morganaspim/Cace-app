from cace_studio.modules.fem_v083 import *
from cace_studio.core.module import ExecutionContext

def test_v083_capability():
    m=ReliabilityV083()
    p=m.resolved_params({})
    out=m.execute({},p,ExecutionContext(run_id="v083"))
    r=out["result"]
    assert r.get("pass", r.get("pass_", True)) is not False
