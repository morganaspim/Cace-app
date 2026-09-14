from cace_studio.modules.production_v258 import *
from cace_studio.core.module import ExecutionContext

def test_production_v258():
    m=ProductionV258()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v258"))
    r=out["result"]
    assert r.get("pass",True) is not False
