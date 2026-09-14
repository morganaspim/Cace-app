from cace_studio.modules.quality_v144 import *
from cace_studio.core.module import ExecutionContext

def test_quality_v144():
    m=QualityV144()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v144"))
    r=out["result"]
    assert r.get("pass",True) is not False
