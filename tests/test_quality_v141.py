from cace_studio.modules.quality_v141 import *
from cace_studio.core.module import ExecutionContext

def test_quality_v141():
    m=QualityV141()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v141"))
    r=out["result"]
    assert r.get("pass",True) is not False
