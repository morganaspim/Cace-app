from cace_studio.modules.next_v209 import *
from cace_studio.core.module import ExecutionContext

def test_next_v209():
    m=NextV209()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v209"))
    r=out["result"]
    assert r.get("pass",True) is not False
    assert r["pass"] is True
