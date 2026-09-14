from cace_studio.modules.next_v204 import *
from cace_studio.core.module import ExecutionContext

def test_next_v204():
    m=NextV204()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v204"))
    r=out["result"]
    assert r.get("pass",True) is not False
