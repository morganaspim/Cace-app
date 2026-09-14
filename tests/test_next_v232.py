from cace_studio.modules.next_v232 import *
from cace_studio.core.module import ExecutionContext

def test_next_v232():
    m=NextV232()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v232"))
    r=out["result"]
    assert r.get("pass",True) is not False
