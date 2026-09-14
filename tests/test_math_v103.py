from cace_studio.modules.math_v103 import *
from cace_studio.core.module import ExecutionContext

def test_math_v103():
    m=MathV103()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v103"))
    r=out["result"]
    assert r.get("pass",True) is not False
