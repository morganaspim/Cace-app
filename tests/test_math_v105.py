from cace_studio.modules.math_v105 import *
from cace_studio.core.module import ExecutionContext

def test_math_v105():
    m=MathV105()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v105"))
    r=out["result"]
    assert r.get("pass",True) is not False
