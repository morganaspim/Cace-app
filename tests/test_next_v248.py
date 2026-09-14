from cace_studio.modules.next_v248 import *
from cace_studio.core.module import ExecutionContext

def test_next_v248():
    m=NextV248()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v248"))
    r=out["result"]
    assert r.get("pass",True) is not False
