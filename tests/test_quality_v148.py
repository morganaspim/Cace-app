from cace_studio.modules.quality_v148 import *
from cace_studio.core.module import ExecutionContext

def test_quality_v148():
    m=QualityV148()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v148"))
    r=out["result"]
    assert r.get("pass",True) is not False
