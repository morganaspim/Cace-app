from cace_studio.modules.next_v221 import *
from cace_studio.core.module import ExecutionContext

def test_next_v221():
    m=NextV221()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v221"))
    r=out["result"]
    assert r.get("pass",True) is not False
