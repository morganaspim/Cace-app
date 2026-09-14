from cace_studio.modules.quality_v143 import *
from cace_studio.core.module import ExecutionContext

def test_quality_v143():
    m=QualityV143()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v143"))
    r=out["result"]
    assert r.get("pass",True) is not False
