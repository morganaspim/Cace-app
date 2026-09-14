from cace_studio.modules.roadmap_v199 import *
from cace_studio.core.module import ExecutionContext

def test_road_v199():
    m=RoadV199()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v199"))
    r=out["result"]
    assert r.get("pass",True) is not False
