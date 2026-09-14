from cace_studio.modules.math_v122 import *
from cace_studio.core.module import ExecutionContext

def test_math_v122():
    m=MathV122()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v122"))
    r=out["result"]
    assert r.get("pass",True) is not False
