from cace_studio.modules.math_v119 import *
from cace_studio.core.module import ExecutionContext

def test_math_v119():
    m=MathV119()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v119"))
    r=out["result"]
    assert r.get("pass",True) is not False
