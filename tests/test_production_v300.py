from cace_studio.modules.production_v300 import *
from cace_studio.core.module import ExecutionContext

def test_production_v300():
    m=ProductionV300()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v300"))
    r=out["result"]
    assert r.get("pass",True) is not False
    assert r["pass"] is True
    assert r["lean_available"] is False
