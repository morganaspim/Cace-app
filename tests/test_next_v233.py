from cace_studio.modules.next_v233 import *
from cace_studio.core.module import ExecutionContext

def test_next_v233():
    m=NextV233()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v233"))
    r=out["result"]
    assert r.get("pass",True) is not False
