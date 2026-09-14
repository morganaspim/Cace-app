from cace_studio.modules.roadmap_v195 import *
from cace_studio.core.module import ExecutionContext

def test_road_v195():
    m=RoadV195()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v195"))
    r=out["result"]
    assert r.get("pass",True) is not False
    assert r["production_nedelec_basis"] is False
