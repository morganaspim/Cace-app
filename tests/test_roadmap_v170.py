from cace_studio.modules.roadmap_v170 import *
from cace_studio.core.module import ExecutionContext

def test_road_v170():
    m=RoadV170()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v170"))
    r=out["result"]
    assert r.get("pass",True) is not False
