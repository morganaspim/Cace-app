from cace_studio.modules.next_v227 import *
from cace_studio.core.module import ExecutionContext

def test_next_v227():
    m=NextV227()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v227"))
    r=out["result"]
    assert r.get("pass",True) is not False
