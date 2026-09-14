from cace_studio.modules.math_v110 import *
from cace_studio.core.module import ExecutionContext

def test_math_v110():
    m=MathV110()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v110"))
    r=out["result"]
    assert r.get("pass",True) is not False
