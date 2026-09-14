from cace_studio.modules.roadmap_v176 import *
from cace_studio.core.module import ExecutionContext

def test_road_v176():
    m=RoadV176()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v176"))
    r=out["result"]
    assert r.get("pass",True) is not False
