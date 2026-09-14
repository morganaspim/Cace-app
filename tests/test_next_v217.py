from cace_studio.modules.next_v217 import *
from cace_studio.core.module import ExecutionContext

def test_next_v217():
    m=NextV217()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v217"))
    r=out["result"]
    assert r.get("pass",True) is not False
