from cace_studio.modules.production_v283 import *
from cace_studio.core.module import ExecutionContext

def test_production_v283():
    m=ProductionV283()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v283"))
    r=out["result"]
    assert r.get("pass",True) is not False
