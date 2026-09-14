from cace_studio.modules.math_v123 import *
from cace_studio.core.module import ExecutionContext

def test_math_v123():
    m=MathV123()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v123"))
    r=out["result"]
    assert r.get("pass",True) is not False
