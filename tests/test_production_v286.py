from cace_studio.modules.production_v286 import *
from cace_studio.core.module import ExecutionContext

def test_production_v286():
    m=ProductionV286()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v286"))
    r=out["result"]
    assert r.get("pass",True) is not False
