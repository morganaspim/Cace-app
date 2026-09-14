from cace_studio.modules.formal_v307 import *
from cace_studio.core.module import ExecutionContext

def test_formal_v307():
    m=FormalV307()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v307"))
    r=out["result"]
    assert r.get("pass",True) is not False
