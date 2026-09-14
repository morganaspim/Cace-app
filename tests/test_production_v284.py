from cace_studio.modules.production_v284 import *
from cace_studio.core.module import ExecutionContext

def test_production_v284():
    m=ProductionV284()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v284"))
    r=out["result"]
    assert r.get("pass",True) is not False
