from cace_studio.modules.math_v107 import *
from cace_studio.core.module import ExecutionContext

def test_math_v107():
    m=MathV107()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v107"))
    r=out["result"]
    assert r.get("pass",True) is not False
