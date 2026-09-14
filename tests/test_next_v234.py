from cace_studio.modules.next_v234 import *
from cace_studio.core.module import ExecutionContext

def test_next_v234():
    m=NextV234()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v234"))
    r=out["result"]
    assert r.get("pass",True) is not False
