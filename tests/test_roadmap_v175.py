from cace_studio.modules.roadmap_v175 import *
from cace_studio.core.module import ExecutionContext

def test_road_v175():
    m=RoadV175()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v175"))
    r=out["result"]
    assert r.get("pass",True) is not False
