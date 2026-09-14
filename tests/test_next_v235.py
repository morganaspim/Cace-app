from cace_studio.modules.next_v235 import *
from cace_studio.core.module import ExecutionContext

def test_next_v235():
    m=NextV235()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v235"))
    r=out["result"]
    assert r.get("pass",True) is not False
