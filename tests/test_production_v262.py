from cace_studio.modules.production_v262 import *
from cace_studio.core.module import ExecutionContext

def test_production_v262():
    m=ProductionV262()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v262"))
    r=out["result"]
    assert r.get("pass",True) is not False
