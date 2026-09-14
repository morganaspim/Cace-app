from cace_studio.modules.formal_v318 import *
from cace_studio.core.module import ExecutionContext

def test_formal_v318():
    m=FormalV318()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v318"))
    r=out["result"]
    assert r.get("pass",True) is not False
