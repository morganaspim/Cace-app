from cace_studio.modules.quality_v134 import *
from cace_studio.core.module import ExecutionContext

def test_quality_v134():
    m=QualityV134()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v134"))
    r=out["result"]
    assert r.get("pass",True) is not False
