from cace_studio.modules.fem_v084 import *
from cace_studio.core.module import ExecutionContext

def test_v084_capability():
    m=ReliabilityV084()
    p=m.resolved_params({})
    out=m.execute({},p,ExecutionContext(run_id="v084"))
    r=out["result"]
    assert r.get("pass", r.get("pass_", True)) is not False
