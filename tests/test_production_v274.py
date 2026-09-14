from cace_studio.modules.production_v274 import *
from cace_studio.core.module import ExecutionContext

def test_production_v274():
    m=ProductionV274()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v274"))
    r=out["result"]
    assert r.get("pass",True) is not False
