from cace_studio.modules.math_v111 import *
from cace_studio.core.module import ExecutionContext

def test_math_v111():
    m=MathV111()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v111"))
    r=out["result"]
    assert r.get("pass",True) is not False
