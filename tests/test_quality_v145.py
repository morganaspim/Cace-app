from cace_studio.modules.quality_v145 import *
from cace_studio.core.module import ExecutionContext

def test_quality_v145():
    m=QualityV145()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v145"))
    r=out["result"]
    assert r.get("pass",True) is not False
    assert r["rt1_production"] is False
    assert r["stiffness"]["pass"] is True
