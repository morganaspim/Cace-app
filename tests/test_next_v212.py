from cace_studio.modules.next_v212 import *
from cace_studio.core.module import ExecutionContext

def test_next_v212():
    m=NextV212()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v212"))
    r=out["result"]
    assert r.get("pass",True) is not False
