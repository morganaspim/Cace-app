from cace_studio.modules.production_v298 import *
from cace_studio.core.module import ExecutionContext

def test_production_v298():
    m=ProductionV298()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v298"))
    r=out["result"]
    assert r.get("pass",True) is not False
