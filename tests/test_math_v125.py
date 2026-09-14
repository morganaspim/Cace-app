from cace_studio.modules.math_v125 import *
from cace_studio.core.module import ExecutionContext

def test_math_v125():
    m=MathV125()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v125"))
    r=out["result"]
    assert r.get("pass",True) is not False
    assert len(r["items"]) == 10
    assert r["formal_promotion"] is False
