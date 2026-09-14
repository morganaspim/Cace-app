from cace_studio.modules.roadmap_v200 import *
from cace_studio.core.module import ExecutionContext

def test_road_v200():
    m=RoadV200()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v200"))
    r=out["result"]
    assert r.get("pass",True) is not False
    assert r["qualification"]["passed"] == r["qualification"]["total"]
