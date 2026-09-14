from cace_studio.modules.next_v216 import *
from cace_studio.core.module import ExecutionContext

def test_next_v216():
    m=NextV216()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v216"))
    r=out["result"]
    assert r.get("pass",True) is not False
