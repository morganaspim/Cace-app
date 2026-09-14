from cace_studio.modules.roadmap_v172 import *
from cace_studio.core.module import ExecutionContext

def test_road_v172():
    m=RoadV172()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v172"))
    r=out["result"]
    assert r.get("pass",True) is not False
