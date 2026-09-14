from cace_studio.modules.roadmap_v157 import *
from cace_studio.core.module import ExecutionContext

def test_road_v157():
    m=RoadV157()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v157"))
    r=out["result"]
    assert r.get("pass",True) is not False
