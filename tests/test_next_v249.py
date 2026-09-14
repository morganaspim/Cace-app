from cace_studio.modules.next_v249 import *
from cace_studio.core.module import ExecutionContext

def test_next_v249():
    m=NextV249()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v249"))
    r=out["result"]
    assert r.get("pass",True) is not False
