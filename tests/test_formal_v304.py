from cace_studio.modules.formal_v304 import *
from cace_studio.core.module import ExecutionContext

def test_formal_v304():
    m=FormalV304()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v304"))
    r=out["result"]
    assert r.get("pass",True) is not False
