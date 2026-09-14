from cace_studio.modules.math_v113 import *
from cace_studio.core.module import ExecutionContext

def test_math_v113():
    m=MathV113()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v113"))
    r=out["result"]
    assert r.get("pass",True) is not False
