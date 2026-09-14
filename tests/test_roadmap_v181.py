from cace_studio.modules.roadmap_v181 import *
from cace_studio.core.module import ExecutionContext

def test_road_v181():
    m=RoadV181()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v181"))
    r=out["result"]
    assert r.get("pass",True) is not False
