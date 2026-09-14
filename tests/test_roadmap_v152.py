from cace_studio.modules.roadmap_v152 import *
from cace_studio.core.module import ExecutionContext

def test_road_v152():
    m=RoadV152()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v152"))
    r=out["result"]
    assert r.get("pass",True) is not False
