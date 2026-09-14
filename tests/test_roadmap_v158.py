from cace_studio.modules.roadmap_v158 import *
from cace_studio.core.module import ExecutionContext

def test_road_v158():
    m=RoadV158()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v158"))
    r=out["result"]
    assert r.get("pass",True) is not False
