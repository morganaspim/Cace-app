from cace_studio.modules.quality_v142 import *
from cace_studio.core.module import ExecutionContext

def test_quality_v142():
    m=QualityV142()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v142"))
    r=out["result"]
    assert r.get("pass",True) is not False
