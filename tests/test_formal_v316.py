from cace_studio.modules.formal_v316 import *
from cace_studio.core.module import ExecutionContext

def test_formal_v316():
    m=FormalV316()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v316"))
    r=out["result"]
    assert r.get("pass",True) is not False
