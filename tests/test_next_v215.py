from cace_studio.modules.next_v215 import *
from cace_studio.core.module import ExecutionContext

def test_next_v215():
    m=NextV215()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v215"))
    r=out["result"]
    assert r.get("pass",True) is not False
