from cace_studio.modules.roadmap_v197 import *
from cace_studio.core.module import ExecutionContext

def test_road_v197():
    m=RoadV197()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v197"))
    r=out["result"]
    assert r.get("pass",True) is not False
