from cace_studio.modules.formal_v308 import *
from cace_studio.core.module import ExecutionContext

def test_formal_v308():
    m=FormalV308()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v308"))
    r=out["result"]
    assert r.get("pass",True) is not False
