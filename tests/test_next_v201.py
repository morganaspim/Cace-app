from cace_studio.modules.next_v201 import *
from cace_studio.core.module import ExecutionContext

def test_next_v201():
    m=NextV201()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v201"))
    r=out["result"]
    assert r.get("pass",True) is not False
