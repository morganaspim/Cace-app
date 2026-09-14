from cace_studio.modules.production_v294 import *
from cace_studio.core.module import ExecutionContext

def test_production_v294():
    m=ProductionV294()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v294"))
    r=out["result"]
    assert r.get("pass",True) is not False
