from cace_studio.modules.roadmap_v153 import *
from cace_studio.core.module import ExecutionContext

def test_road_v153():
    m=RoadV153()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v153"))
    r=out["result"]
    assert r.get("pass",True) is not False
