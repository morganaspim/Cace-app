from cace_studio.modules.roadmap_v177 import *
from cace_studio.core.module import ExecutionContext

def test_road_v177():
    m=RoadV177()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v177"))
    r=out["result"]
    assert r.get("pass",True) is not False
