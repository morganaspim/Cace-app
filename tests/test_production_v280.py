from cace_studio.modules.production_v280 import *
from cace_studio.core.module import ExecutionContext

def test_production_v280():
    m=ProductionV280()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v280"))
    r=out["result"]
    assert r.get("pass",True) is not False
