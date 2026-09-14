from cace_studio.modules.quality_v150 import *
from cace_studio.core.module import ExecutionContext

def test_quality_v150():
    m=QualityV150()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v150"))
    r=out["result"]
    assert r.get("pass",True) is not False
    assert r["formal_dwr_theorem"] is False
