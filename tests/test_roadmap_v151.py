from cace_studio.modules.roadmap_v151 import *
from cace_studio.core.module import ExecutionContext

def test_road_v151():
    m=RoadV151()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v151"))
    r=out["result"]
    assert r.get("pass",True) is not False
