from cace_studio.modules.next_v218 import *
from cace_studio.core.module import ExecutionContext

def test_next_v218():
    m=NextV218()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v218"))
    r=out["result"]
    assert r.get("pass",True) is not False
