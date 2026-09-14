from cace_studio.modules.production_v253 import *
from cace_studio.core.module import ExecutionContext

def test_production_v253():
    m=ProductionV253()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v253"))
    r=out["result"]
    assert r.get("pass",True) is not False
