from cace_studio.modules.roadmap_v192 import *
from cace_studio.core.module import ExecutionContext

def test_road_v192():
    m=RoadV192()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v192"))
    r=out["result"]
    assert r.get("pass",True) is not False
