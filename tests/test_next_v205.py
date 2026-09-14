from cace_studio.modules.next_v205 import *
from cace_studio.core.module import ExecutionContext

def test_next_v205():
    m=NextV205()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v205"))
    r=out["result"]
    assert r.get("pass",True) is not False
