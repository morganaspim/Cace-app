from cace_studio.modules.math_v108 import *
from cace_studio.core.module import ExecutionContext

def test_math_v108():
    m=MathV108()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v108"))
    r=out["result"]
    assert r.get("pass",True) is not False
