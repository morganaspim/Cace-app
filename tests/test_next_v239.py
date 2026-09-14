from cace_studio.modules.next_v239 import *
from cace_studio.core.module import ExecutionContext

def test_next_v239():
    m=NextV239()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v239"))
    r=out["result"]
    assert r.get("pass",True) is not False
