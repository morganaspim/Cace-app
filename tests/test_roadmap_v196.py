from cace_studio.modules.roadmap_v196 import *
from cace_studio.core.module import ExecutionContext

def test_road_v196():
    m=RoadV196()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v196"))
    r=out["result"]
    assert r.get("pass",True) is not False
