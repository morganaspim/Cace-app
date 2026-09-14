from cace_studio.modules.production_v290 import *
from cace_studio.core.module import ExecutionContext

def test_production_v290():
    m=ProductionV290()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v290"))
    r=out["result"]
    assert r.get("pass",True) is not False
