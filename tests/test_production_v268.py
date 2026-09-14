from cace_studio.modules.production_v268 import *
from cace_studio.core.module import ExecutionContext

def test_production_v268():
    m=ProductionV268()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v268"))
    r=out["result"]
    assert r.get("pass",True) is not False
