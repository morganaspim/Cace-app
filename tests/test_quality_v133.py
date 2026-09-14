from cace_studio.modules.quality_v133 import *
from cace_studio.core.module import ExecutionContext

def test_quality_v133():
    m=QualityV133()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v133"))
    r=out["result"]
    assert r.get("pass",True) is not False
    assert r["improved_or_equal"] is True
