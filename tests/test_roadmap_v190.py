from cace_studio.modules.roadmap_v190 import *
from cace_studio.core.module import ExecutionContext

def test_road_v190():
    m=RoadV190()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v190"))
    r=out["result"]
    assert r.get("pass",True) is not False
