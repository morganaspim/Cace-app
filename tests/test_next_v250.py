from cace_studio.modules.next_v250 import *
from cace_studio.core.module import ExecutionContext

def test_next_v250():
    m=NextV250()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v250"))
    r=out["result"]
    assert r.get("pass",True) is not False
    assert r["selected25"]["pass"] is True
