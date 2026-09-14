from cace_studio.modules.math_v104 import *
from cace_studio.core.module import ExecutionContext

def test_math_v104():
    m=MathV104()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v104"))
    r=out["result"]
    assert r.get("pass",True) is not False
