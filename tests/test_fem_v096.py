from cace_studio.modules.fem_v096 import *
from cace_studio.core.module import ExecutionContext

def test_v096_capability():
    m=ReliabilityV096()
    p=m.resolved_params({})
    out=m.execute({},p,ExecutionContext(run_id="v096"))
    r=out["result"]
    assert r.get("pass", r.get("pass_", True)) is not False
