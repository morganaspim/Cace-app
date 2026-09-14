from cace_studio.modules.production_v299 import *
from cace_studio.core.module import ExecutionContext

def test_production_v299():
    m=ProductionV299()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v299"))
    r=out["result"]
    assert r.get("pass",True) is not False
