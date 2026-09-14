from cace_studio.modules.quality_v132 import *
from cace_studio.core.module import ExecutionContext

def test_quality_v132():
    m=QualityV132()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v132"))
    r=out["result"]
    assert r.get("pass",True) is not False
