from cace_studio.modules.next_v222 import *
from cace_studio.core.module import ExecutionContext

def test_next_v222():
    m=NextV222()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v222"))
    r=out["result"]
    assert r.get("pass",True) is not False
