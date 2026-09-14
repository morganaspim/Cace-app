from cace_studio.modules.math_v117 import *
from cace_studio.core.module import ExecutionContext

def test_math_v117():
    m=MathV117()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v117"))
    r=out["result"]
    assert r.get("pass",True) is not False
