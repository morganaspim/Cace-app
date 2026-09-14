from cace_studio.modules.roadmap_v167 import *
from cace_studio.core.module import ExecutionContext

def test_road_v167():
    m=RoadV167()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v167"))
    r=out["result"]
    assert r.get("pass",True) is not False
