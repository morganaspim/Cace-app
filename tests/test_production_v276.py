from cace_studio.modules.production_v276 import *
from cace_studio.core.module import ExecutionContext

def test_production_v276():
    m=ProductionV276()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v276"))
    r=out["result"]
    assert r.get("pass",True) is not False
