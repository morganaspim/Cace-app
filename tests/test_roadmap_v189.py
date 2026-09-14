from cace_studio.modules.roadmap_v189 import *
from cace_studio.core.module import ExecutionContext

def test_road_v189():
    m=RoadV189()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v189"))
    r=out["result"]
    assert r.get("pass",True) is not False
