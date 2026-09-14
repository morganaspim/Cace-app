from cace_studio.modules.roadmap_v162 import *
from cace_studio.core.module import ExecutionContext

def test_road_v162():
    m=RoadV162()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v162"))
    r=out["result"]
    assert r.get("pass",True) is not False
