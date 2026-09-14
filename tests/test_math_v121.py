from cace_studio.modules.math_v121 import *
from cace_studio.core.module import ExecutionContext

def test_math_v121():
    m=MathV121()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v121"))
    r=out["result"]
    assert r.get("pass",True) is not False
