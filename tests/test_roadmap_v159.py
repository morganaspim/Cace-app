from cace_studio.modules.roadmap_v159 import *
from cace_studio.core.module import ExecutionContext

def test_road_v159():
    m=RoadV159()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v159"))
    r=out["result"]
    assert r.get("pass",True) is not False
