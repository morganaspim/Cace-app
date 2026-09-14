from cace_studio.modules.next_v243 import *
from cace_studio.core.module import ExecutionContext

def test_next_v243():
    m=NextV243()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v243"))
    r=out["result"]
    assert r.get("pass",True) is not False
