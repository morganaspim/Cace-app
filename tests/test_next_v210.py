from cace_studio.modules.next_v210 import *
from cace_studio.core.module import ExecutionContext

def test_next_v210():
    m=NextV210()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v210"))
    r=out["result"]
    assert r.get("pass",True) is not False
