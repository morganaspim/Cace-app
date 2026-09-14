from cace_studio.modules.next_v225 import *
from cace_studio.core.module import ExecutionContext

def test_next_v225():
    m=NextV225()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v225"))
    r=out["result"]
    assert r.get("pass",True) is not False
    assert r["selected_14"]["pass"] is True
