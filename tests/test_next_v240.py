from cace_studio.modules.next_v240 import *
from cace_studio.core.module import ExecutionContext

def test_next_v240():
    m=NextV240()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v240"))
    r=out["result"]
    assert r.get("pass",True) is not False
