from cace_studio.modules.roadmap_v187 import *
from cace_studio.core.module import ExecutionContext

def test_road_v187():
    m=RoadV187()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v187"))
    r=out["result"]
    assert r.get("pass",True) is not False
