from cace_studio.modules.next_v230 import *
from cace_studio.core.module import ExecutionContext

def test_next_v230():
    m=NextV230()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v230"))
    r=out["result"]
    assert r.get("pass",True) is not False
