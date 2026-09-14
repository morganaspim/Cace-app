from cace_studio.modules.production_v292 import *
from cace_studio.core.module import ExecutionContext

def test_production_v292():
    m=ProductionV292()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v292"))
    r=out["result"]
    assert r.get("pass",True) is not False
