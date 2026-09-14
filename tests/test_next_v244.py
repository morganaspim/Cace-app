from cace_studio.modules.next_v244 import *
from cace_studio.core.module import ExecutionContext

def test_next_v244():
    m=NextV244()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v244"))
    r=out["result"]
    assert r.get("pass",True) is not False
