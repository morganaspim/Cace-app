from cace_studio.modules.quality_v140 import *
from cace_studio.core.module import ExecutionContext

def test_quality_v140():
    m=QualityV140()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v140"))
    r=out["result"]
    assert r.get("pass",True) is not False
