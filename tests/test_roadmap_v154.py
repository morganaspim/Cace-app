from cace_studio.modules.roadmap_v154 import *
from cace_studio.core.module import ExecutionContext

def test_road_v154():
    m=RoadV154()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v154"))
    r=out["result"]
    assert r.get("pass",True) is not False
