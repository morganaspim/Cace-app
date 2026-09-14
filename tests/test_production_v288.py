from cace_studio.modules.production_v288 import *
from cace_studio.core.module import ExecutionContext

def test_production_v288():
    m=ProductionV288()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v288"))
    r=out["result"]
    assert r.get("pass",True) is not False
