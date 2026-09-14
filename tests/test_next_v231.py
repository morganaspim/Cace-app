from cace_studio.modules.next_v231 import *
from cace_studio.core.module import ExecutionContext

def test_next_v231():
    m=NextV231()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v231"))
    r=out["result"]
    assert r.get("pass",True) is not False
