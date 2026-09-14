from cace_studio.modules.production_v260 import *
from cace_studio.core.module import ExecutionContext

def test_production_v260():
    m=ProductionV260()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v260"))
    r=out["result"]
    assert r.get("pass",True) is not False
