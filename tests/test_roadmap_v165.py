from cace_studio.modules.roadmap_v165 import *
from cace_studio.core.module import ExecutionContext

def test_road_v165():
    m=RoadV165()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v165"))
    r=out["result"]
    assert r.get("pass",True) is not False
    assert r["continuum_goal_error_guaranteed"] is False
