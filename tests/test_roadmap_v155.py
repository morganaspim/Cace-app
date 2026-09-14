from cace_studio.modules.roadmap_v155 import *
from cace_studio.core.module import ExecutionContext

def test_road_v155():
    m=RoadV155()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v155"))
    r=out["result"]
    assert r.get("pass",True) is not False
    assert r["production_global_RT1"] is False
