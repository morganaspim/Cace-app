from cace_studio.modules.roadmap_v174 import *
from cace_studio.core.module import ExecutionContext

def test_road_v174():
    m=RoadV174()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v174"))
    r=out["result"]
    assert r.get("pass",True) is not False
