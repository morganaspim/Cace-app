from cace_studio.modules.quality_v139 import *
from cace_studio.core.module import ExecutionContext

def test_quality_v139():
    m=QualityV139()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v139"))
    r=out["result"]
    assert r.get("pass",True) is not False
