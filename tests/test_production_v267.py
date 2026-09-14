from cace_studio.modules.production_v267 import *
from cace_studio.core.module import ExecutionContext

def test_production_v267():
    m=ProductionV267()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v267"))
    r=out["result"]
    assert r.get("pass",True) is not False
