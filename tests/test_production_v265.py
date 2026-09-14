from cace_studio.modules.production_v265 import *
from cace_studio.core.module import ExecutionContext

def test_production_v265():
    m=ProductionV265()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v265"))
    r=out["result"]
    assert r.get("pass",True) is not False
