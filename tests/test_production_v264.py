from cace_studio.modules.production_v264 import *
from cace_studio.core.module import ExecutionContext

def test_production_v264():
    m=ProductionV264()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v264"))
    r=out["result"]
    assert r.get("pass",True) is not False
