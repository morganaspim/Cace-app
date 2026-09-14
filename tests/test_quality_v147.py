from cace_studio.modules.quality_v147 import *
from cace_studio.core.module import ExecutionContext

def test_quality_v147():
    m=QualityV147()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v147"))
    r=out["result"]
    assert r.get("pass",True) is not False
