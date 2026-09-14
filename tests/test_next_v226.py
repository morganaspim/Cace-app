from cace_studio.modules.next_v226 import *
from cace_studio.core.module import ExecutionContext

def test_next_v226():
    m=NextV226()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v226"))
    r=out["result"]
    assert r.get("pass",True) is not False
