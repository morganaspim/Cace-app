from cace_studio.modules.math_v118 import *
from cace_studio.core.module import ExecutionContext

def test_math_v118():
    m=MathV118()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v118"))
    r=out["result"]
    assert r.get("pass",True) is not False
