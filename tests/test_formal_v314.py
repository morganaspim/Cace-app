from cace_studio.modules.formal_v314 import *
from cace_studio.core.module import ExecutionContext

def test_formal_v314():
    m=FormalV314()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v314"))
    r=out["result"]
    assert r.get("pass",True) is not False
