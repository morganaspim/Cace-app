from cace_studio.modules.quality_v131 import *
from cace_studio.core.module import ExecutionContext

def test_quality_v131():
    m=QualityV131()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v131"))
    r=out["result"]
    assert r.get("pass",True) is not False
