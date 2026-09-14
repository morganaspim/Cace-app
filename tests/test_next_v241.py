from cace_studio.modules.next_v241 import *
from cace_studio.core.module import ExecutionContext

def test_next_v241():
    m=NextV241()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v241"))
    r=out["result"]
    assert r.get("pass",True) is not False
