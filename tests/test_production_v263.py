from cace_studio.modules.production_v263 import *
from cace_studio.core.module import ExecutionContext

def test_production_v263():
    m=ProductionV263()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v263"))
    r=out["result"]
    assert r.get("pass",True) is not False
