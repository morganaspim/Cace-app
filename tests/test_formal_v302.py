from cace_studio.modules.formal_v302 import *
from cace_studio.core.module import ExecutionContext

def test_formal_v302():
    m=FormalV302()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v302"))
    r=out["result"]
    assert r.get("pass",True) is not False
