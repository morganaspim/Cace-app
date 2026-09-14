from cace_studio.modules.roadmap_v163 import *
from cace_studio.core.module import ExecutionContext

def test_road_v163():
    m=RoadV163()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v163"))
    r=out["result"]
    assert r.get("pass",True) is not False
