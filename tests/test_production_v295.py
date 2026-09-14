from cace_studio.modules.production_v295 import *
from cace_studio.core.module import ExecutionContext

def test_production_v295():
    m=ProductionV295()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v295"))
    r=out["result"]
    assert r.get("pass",True) is not False
