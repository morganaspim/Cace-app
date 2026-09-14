from cace_studio.modules.formal_v311 import *
from cace_studio.core.module import ExecutionContext

def test_formal_v311():
    m=FormalV311()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v311"))
    r=out["result"]
    assert r.get("pass",True) is not False
