from cace_studio.modules.next_v214 import *
from cace_studio.core.module import ExecutionContext

def test_next_v214():
    m=NextV214()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v214"))
    r=out["result"]
    assert r.get("pass",True) is not False
