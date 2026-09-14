from cace_studio.modules.next_v223 import *
from cace_studio.core.module import ExecutionContext

def test_next_v223():
    m=NextV223()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v223"))
    r=out["result"]
    assert r.get("pass",True) is not False
    assert r["solution_interval"][0] <= r["solution_interval"][1]
