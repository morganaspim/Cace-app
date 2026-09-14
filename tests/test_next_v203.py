from cace_studio.modules.next_v203 import *
from cace_studio.core.module import ExecutionContext

def test_next_v203():
    m=NextV203()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v203"))
    r=out["result"]
    assert r.get("pass",True) is not False
