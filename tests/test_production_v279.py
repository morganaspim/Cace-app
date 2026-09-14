from cace_studio.modules.production_v279 import *
from cace_studio.core.module import ExecutionContext

def test_production_v279():
    m=ProductionV279()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v279"))
    r=out["result"]
    assert r.get("pass",True) is not False
