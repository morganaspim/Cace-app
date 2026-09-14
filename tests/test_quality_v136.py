from cace_studio.modules.quality_v136 import *
from cace_studio.core.module import ExecutionContext

def test_quality_v136():
    m=QualityV136()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v136"))
    r=out["result"]
    assert r.get("pass",True) is not False
