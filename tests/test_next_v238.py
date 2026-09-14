from cace_studio.modules.next_v238 import *
from cace_studio.core.module import ExecutionContext

def test_next_v238():
    m=NextV238()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v238"))
    r=out["result"]
    assert r.get("pass",True) is not False
