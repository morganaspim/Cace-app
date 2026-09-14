from cace_studio.modules.roadmap_v160 import *
from cace_studio.core.module import ExecutionContext

def test_road_v160():
    m=RoadV160()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v160"))
    r=out["result"]
    assert r.get("pass",True) is not False
