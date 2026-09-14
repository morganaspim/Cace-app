from cace_studio.modules.roadmap_v178 import *
from cace_studio.core.module import ExecutionContext

def test_road_v178():
    m=RoadV178()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v178"))
    r=out["result"]
    assert r.get("pass",True) is not False
