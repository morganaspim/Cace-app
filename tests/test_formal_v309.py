from cace_studio.modules.formal_v309 import *
from cace_studio.core.module import ExecutionContext

def test_formal_v309():
    m=FormalV309()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v309"))
    r=out["result"]
    assert r.get("pass",True) is not False
