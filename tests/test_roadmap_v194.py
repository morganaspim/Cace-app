from cace_studio.modules.roadmap_v194 import *
from cace_studio.core.module import ExecutionContext

def test_road_v194():
    m=RoadV194()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v194"))
    r=out["result"]
    assert r.get("pass",True) is not False
