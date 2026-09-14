from cace_studio.modules.production_v269 import *
from cace_studio.core.module import ExecutionContext

def test_production_v269():
    m=ProductionV269()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v269"))
    r=out["result"]
    assert r.get("pass",True) is not False
