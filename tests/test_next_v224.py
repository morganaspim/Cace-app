from cace_studio.modules.next_v224 import *
from cace_studio.core.module import ExecutionContext

def test_next_v224():
    m=NextV224()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v224"))
    r=out["result"]
    assert r.get("pass",True) is not False
