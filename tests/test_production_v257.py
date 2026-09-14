from cace_studio.modules.production_v257 import *
from cace_studio.core.module import ExecutionContext

def test_production_v257():
    m=ProductionV257()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v257"))
    r=out["result"]
    assert r.get("pass",True) is not False
