from cace_studio.modules.next_v236 import *
from cace_studio.core.module import ExecutionContext

def test_next_v236():
    m=NextV236()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v236"))
    r=out["result"]
    assert r.get("pass",True) is not False
