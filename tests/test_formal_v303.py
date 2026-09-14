from cace_studio.modules.formal_v303 import *
from cace_studio.core.module import ExecutionContext

def test_formal_v303():
    m=FormalV303()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v303"))
    r=out["result"]
    assert r.get("pass",True) is not False
