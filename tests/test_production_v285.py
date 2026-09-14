from cace_studio.modules.production_v285 import *
from cace_studio.core.module import ExecutionContext

def test_production_v285():
    m=ProductionV285()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v285"))
    r=out["result"]
    assert r.get("pass",True) is not False
