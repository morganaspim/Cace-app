from cace_studio.modules.next_v206 import *
from cace_studio.core.module import ExecutionContext

def test_next_v206():
    m=NextV206()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v206"))
    r=out["result"]
    assert r.get("pass",True) is not False
