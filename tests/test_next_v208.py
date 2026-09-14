from cace_studio.modules.next_v208 import *
from cace_studio.core.module import ExecutionContext

def test_next_v208():
    m=NextV208()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v208"))
    r=out["result"]
    assert r.get("pass",True) is not False
