from cace_studio.modules.next_v202 import *
from cace_studio.core.module import ExecutionContext

def test_next_v202():
    m=NextV202()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v202"))
    r=out["result"]
    assert r.get("pass",True) is not False
