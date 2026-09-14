from cace_studio.modules.production_v293 import *
from cace_studio.core.module import ExecutionContext

def test_production_v293():
    m=ProductionV293()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v293"))
    r=out["result"]
    assert r.get("pass",True) is not False
