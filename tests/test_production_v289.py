from cace_studio.modules.production_v289 import *
from cace_studio.core.module import ExecutionContext

def test_production_v289():
    m=ProductionV289()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v289"))
    r=out["result"]
    assert r.get("pass",True) is not False
