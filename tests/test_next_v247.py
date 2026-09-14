from cace_studio.modules.next_v247 import *
from cace_studio.core.module import ExecutionContext

def test_next_v247():
    m=NextV247()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v247"))
    r=out["result"]
    assert r.get("pass",True) is not False
