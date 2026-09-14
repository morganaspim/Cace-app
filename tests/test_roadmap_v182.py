from cace_studio.modules.roadmap_v182 import *
from cace_studio.core.module import ExecutionContext

def test_road_v182():
    m=RoadV182()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v182"))
    r=out["result"]
    assert r.get("pass",True) is not False
