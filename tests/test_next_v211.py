from cace_studio.modules.next_v211 import *
from cace_studio.core.module import ExecutionContext

def test_next_v211():
    m=NextV211()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v211"))
    r=out["result"]
    assert r.get("pass",True) is not False
