from cace_studio.modules.math_v102 import *
from cace_studio.core.module import ExecutionContext

def test_math_v102():
    m=MathV102()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v102"))
    r=out["result"]
    assert r.get("pass",True) is not False
