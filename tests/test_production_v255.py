from cace_studio.modules.production_v255 import *
from cace_studio.core.module import ExecutionContext

def test_production_v255():
    m=ProductionV255()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v255"))
    r=out["result"]
    assert r.get("pass",True) is not False
