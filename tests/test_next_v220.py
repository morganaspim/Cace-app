from cace_studio.modules.next_v220 import *
from cace_studio.core.module import ExecutionContext

def test_next_v220():
    m=NextV220()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v220"))
    r=out["result"]
    assert r.get("pass",True) is not False
