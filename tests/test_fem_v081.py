from cace_studio.modules.fem_v081 import *
from cace_studio.core.module import ExecutionContext

def test_v081_capability():
    m=ReliabilityV081()
    p=m.resolved_params({})
    out=m.execute({},p,ExecutionContext(run_id="v081"))
    r=out["result"]
    assert r.get("pass", r.get("pass_", True)) is not False
