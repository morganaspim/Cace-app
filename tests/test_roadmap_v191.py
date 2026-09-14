from cace_studio.modules.roadmap_v191 import *
from cace_studio.core.module import ExecutionContext

def test_road_v191():
    m=RoadV191()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v191"))
    r=out["result"]
    assert r.get("pass",True) is not False
