from cace_studio.modules.roadmap_v168 import *
from cace_studio.core.module import ExecutionContext

def test_road_v168():
    m=RoadV168()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v168"))
    r=out["result"]
    assert r.get("pass",True) is not False
