from cace_studio.modules.math_v109 import *
from cace_studio.core.module import ExecutionContext

def test_math_v109():
    m=MathV109()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v109"))
    r=out["result"]
    assert r.get("pass",True) is not False
