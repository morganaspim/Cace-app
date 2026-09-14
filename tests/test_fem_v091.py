from cace_studio.modules.fem_v091 import *
from cace_studio.core.module import ExecutionContext

def test_v091_capability():
    m=ReliabilityV091()
    p=m.resolved_params({})
    out=m.execute({},p,ExecutionContext(run_id="v091"))
    r=out["result"]
    assert r.get("pass", r.get("pass_", True)) is not False
