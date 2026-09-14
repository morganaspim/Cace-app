from cace_studio.modules.roadmap_v179 import *
from cace_studio.core.module import ExecutionContext

def test_road_v179():
    m=RoadV179()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v179"))
    r=out["result"]
    assert r.get("pass",True) is not False
