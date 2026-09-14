from cace_studio.modules.math_v114 import *
from cace_studio.core.module import ExecutionContext

def test_math_v114():
    m=MathV114()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v114"))
    r=out["result"]
    assert r.get("pass",True) is not False
