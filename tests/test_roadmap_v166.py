from cace_studio.modules.roadmap_v166 import *
from cace_studio.core.module import ExecutionContext

def test_road_v166():
    m=RoadV166()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v166"))
    r=out["result"]
    assert r.get("pass",True) is not False
