from cace_studio.modules.production_v270 import *
from cace_studio.core.module import ExecutionContext

def test_production_v270():
    m=ProductionV270()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v270"))
    r=out["result"]
    assert r.get("pass",True) is not False
    assert r["status"] == "NOT_RUN"
