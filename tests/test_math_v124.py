from cace_studio.modules.math_v124 import *
from cace_studio.core.module import ExecutionContext

def test_math_v124():
    m=MathV124()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v124"))
    r=out["result"]
    assert r.get("pass",True) is not False
