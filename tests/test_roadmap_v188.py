from cace_studio.modules.roadmap_v188 import *
from cace_studio.core.module import ExecutionContext

def test_road_v188():
    m=RoadV188()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v188"))
    r=out["result"]
    assert r.get("pass",True) is not False
