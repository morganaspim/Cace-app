from cace_studio.modules.roadmap_v169 import *
from cace_studio.core.module import ExecutionContext

def test_road_v169():
    m=RoadV169()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v169"))
    r=out["result"]
    assert r.get("pass",True) is not False
