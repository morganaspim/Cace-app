from cace_studio.modules.fem_v082 import *
from cace_studio.core.module import ExecutionContext

def test_v082_capability():
    m=ReliabilityV082()
    p=m.resolved_params({})
    out=m.execute({},p,ExecutionContext(run_id="v082"))
    r=out["result"]
    assert r.get("pass", r.get("pass_", True)) is not False
