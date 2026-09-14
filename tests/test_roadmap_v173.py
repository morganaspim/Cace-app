from cace_studio.modules.roadmap_v173 import *
from cace_studio.core.module import ExecutionContext

def test_road_v173():
    m=RoadV173()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v173"))
    r=out["result"]
    assert r.get("pass",True) is not False
