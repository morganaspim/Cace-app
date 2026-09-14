from cace_studio.modules.quality_v138 import *
from cace_studio.core.module import ExecutionContext

def test_quality_v138():
    m=QualityV138()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v138"))
    r=out["result"]
    assert r.get("pass",True) is not False
