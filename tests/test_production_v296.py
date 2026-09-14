from cace_studio.modules.production_v296 import *
from cace_studio.core.module import ExecutionContext

def test_production_v296():
    m=ProductionV296()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v296"))
    r=out["result"]
    assert r.get("pass",True) is not False
