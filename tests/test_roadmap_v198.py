from cace_studio.modules.roadmap_v198 import *
from cace_studio.core.module import ExecutionContext

def test_road_v198():
    m=RoadV198()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v198"))
    r=out["result"]
    assert r.get("pass",True) is not False
