from cace_studio.modules.next_v245 import *
from cace_studio.core.module import ExecutionContext

def test_next_v245():
    m=NextV245()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v245"))
    r=out["result"]
    assert r.get("pass",True) is not False
