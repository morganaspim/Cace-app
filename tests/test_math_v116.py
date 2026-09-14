from cace_studio.modules.math_v116 import *
from cace_studio.core.module import ExecutionContext

def test_math_v116():
    m=MathV116()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v116"))
    r=out["result"]
    assert r.get("pass",True) is not False
