from cace_studio.modules.production_v297 import *
from cace_studio.core.module import ExecutionContext

def test_production_v297():
    m=ProductionV297()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v297"))
    r=out["result"]
    assert r.get("pass",True) is not False
