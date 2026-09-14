from cace_studio.modules.quality_v137 import *
from cace_studio.core.module import ExecutionContext

def test_quality_v137():
    m=QualityV137()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v137"))
    r=out["result"]
    assert r.get("pass",True) is not False
