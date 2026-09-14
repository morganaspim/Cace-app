from cace_studio.modules.production_v281 import *
from cace_studio.core.module import ExecutionContext

def test_production_v281():
    m=ProductionV281()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v281"))
    r=out["result"]
    assert r.get("pass",True) is not False
