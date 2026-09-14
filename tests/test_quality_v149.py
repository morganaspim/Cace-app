from cace_studio.modules.quality_v149 import *
from cace_studio.core.module import ExecutionContext

def test_quality_v149():
    m=QualityV149()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v149"))
    r=out["result"]
    assert r.get("pass",True) is not False
