from cace_studio.modules.roadmap_v186 import *
from cace_studio.core.module import ExecutionContext

def test_road_v186():
    m=RoadV186()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v186"))
    r=out["result"]
    assert r.get("pass",True) is not False
