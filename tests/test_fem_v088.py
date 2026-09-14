from cace_studio.modules.fem_v088 import *
from cace_studio.core.module import ExecutionContext

def test_v088_capability():
    m=ReliabilityV088()
    p=m.resolved_params({})
    out=m.execute({},p,ExecutionContext(run_id="v088"))
    r=out["result"]
    assert r.get("pass", r.get("pass_", True)) is not False
