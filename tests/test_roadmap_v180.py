from cace_studio.modules.roadmap_v180 import *
from cace_studio.core.module import ExecutionContext

def test_road_v180():
    m=RoadV180()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v180"))
    r=out["result"]
    assert r.get("pass",True) is not False
    assert r["production_RT_mixed_poisson"] is False
