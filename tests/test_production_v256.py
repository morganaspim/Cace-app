from cace_studio.modules.production_v256 import *
from cace_studio.core.module import ExecutionContext

def test_production_v256():
    m=ProductionV256()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v256"))
    r=out["result"]
    assert r.get("pass",True) is not False
