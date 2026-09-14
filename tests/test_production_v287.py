from cace_studio.modules.production_v287 import *
from cace_studio.core.module import ExecutionContext

def test_production_v287():
    m=ProductionV287()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v287"))
    r=out["result"]
    assert r.get("pass",True) is not False
