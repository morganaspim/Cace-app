from cace_studio.modules.next_v237 import *
from cace_studio.core.module import ExecutionContext

def test_next_v237():
    m=NextV237()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v237"))
    r=out["result"]
    assert r.get("pass",True) is not False
