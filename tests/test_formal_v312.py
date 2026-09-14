from cace_studio.modules.formal_v312 import *
from cace_studio.core.module import ExecutionContext

def test_formal_v312():
    m=FormalV312()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v312"))
    r=out["result"]
    assert r.get("pass",True) is not False
