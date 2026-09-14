from cace_studio.modules.production_v261 import *
from cace_studio.core.module import ExecutionContext

def test_production_v261():
    m=ProductionV261()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v261"))
    r=out["result"]
    assert r.get("pass",True) is not False
