from cace_studio.modules.production_v273 import *
from cace_studio.core.module import ExecutionContext

def test_production_v273():
    m=ProductionV273()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v273"))
    r=out["result"]
    assert r.get("pass",True) is not False
