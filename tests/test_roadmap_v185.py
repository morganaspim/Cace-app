from cace_studio.modules.roadmap_v185 import *
from cace_studio.core.module import ExecutionContext

def test_road_v185():
    m=RoadV185()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v185"))
    r=out["result"]
    assert r.get("pass",True) is not False
