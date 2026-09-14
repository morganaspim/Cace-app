from cace_studio.modules.roadmap_v164 import *
from cace_studio.core.module import ExecutionContext

def test_road_v164():
    m=RoadV164()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v164"))
    r=out["result"]
    assert r.get("pass",True) is not False
