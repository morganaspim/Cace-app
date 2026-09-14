from cace_studio.modules.quality_v135 import *
from cace_studio.core.module import ExecutionContext

def test_quality_v135():
    m=QualityV135()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v135"))
    r=out["result"]
    assert r.get("pass",True) is not False
