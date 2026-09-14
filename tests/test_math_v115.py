from cace_studio.modules.math_v115 import *
from cace_studio.core.module import ExecutionContext

def test_math_v115():
    m=MathV115()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v115"))
    r=out["result"]
    assert r.get("pass",True) is not False
