from cace_studio.modules.formal_v317 import *
from cace_studio.core.module import ExecutionContext

def test_formal_v317():
    m=FormalV317()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v317"))
    r=out["result"]
    assert r.get("pass",True) is not False
