from cace_studio.modules.fem_v095 import *
from cace_studio.core.module import ExecutionContext

def test_v095_capability():
    m=ReliabilityV095()
    p=m.resolved_params({})
    out=m.execute({},p,ExecutionContext(run_id="v095"))
    r=out["result"]
    assert r.get("pass", r.get("pass_", True)) is not False
