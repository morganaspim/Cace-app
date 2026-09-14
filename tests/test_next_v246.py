from cace_studio.modules.next_v246 import *
from cace_studio.core.module import ExecutionContext

def test_next_v246():
    m=NextV246()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v246"))
    r=out["result"]
    assert r.get("pass",True) is not False
