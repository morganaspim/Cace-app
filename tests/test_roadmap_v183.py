from cace_studio.modules.roadmap_v183 import *
from cace_studio.core.module import ExecutionContext

def test_road_v183():
    m=RoadV183()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v183"))
    r=out["result"]
    assert r.get("pass",True) is not False
