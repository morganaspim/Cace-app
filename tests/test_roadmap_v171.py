from cace_studio.modules.roadmap_v171 import *
from cace_studio.core.module import ExecutionContext

def test_road_v171():
    m=RoadV171()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v171"))
    r=out["result"]
    assert r.get("pass",True) is not False
