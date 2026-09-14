from cace_studio.modules.next_v207 import *
from cace_studio.core.module import ExecutionContext

def test_next_v207():
    m=NextV207()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v207"))
    r=out["result"]
    assert r.get("pass",True) is not False
