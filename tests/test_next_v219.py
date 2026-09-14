from cace_studio.modules.next_v219 import *
from cace_studio.core.module import ExecutionContext

def test_next_v219():
    m=NextV219()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v219"))
    r=out["result"]
    assert r.get("pass",True) is not False
