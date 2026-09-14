from cace_studio.modules.production_v277 import *
from cace_studio.core.module import ExecutionContext

def test_production_v277():
    m=ProductionV277()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v277"))
    r=out["result"]
    assert r.get("pass",True) is not False
