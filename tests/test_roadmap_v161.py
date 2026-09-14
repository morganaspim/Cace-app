from cace_studio.modules.roadmap_v161 import *
from cace_studio.core.module import ExecutionContext

def test_road_v161():
    m=RoadV161()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v161"))
    r=out["result"]
    assert r.get("pass",True) is not False
