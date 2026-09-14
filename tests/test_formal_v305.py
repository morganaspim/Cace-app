from cace_studio.modules.formal_v305 import *
from cace_studio.core.module import ExecutionContext

def test_formal_v305():
    m=FormalV305()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v305"))
    r=out["result"]
    assert r.get("pass",True) is not False
