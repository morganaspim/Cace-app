from cace_studio.modules.production_v291 import *
from cace_studio.core.module import ExecutionContext

def test_production_v291():
    m=ProductionV291()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v291"))
    r=out["result"]
    assert r.get("pass",True) is not False
