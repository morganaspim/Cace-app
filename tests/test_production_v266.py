from cace_studio.modules.production_v266 import *
from cace_studio.core.module import ExecutionContext

def test_production_v266():
    m=ProductionV266()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v266"))
    r=out["result"]
    assert r.get("pass",True) is not False
