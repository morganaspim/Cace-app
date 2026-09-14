from cace_studio.modules.production_v271 import *
from cace_studio.core.module import ExecutionContext

def test_production_v271():
    m=ProductionV271()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v271"))
    r=out["result"]
    assert r.get("pass",True) is not False
    assert r["full_machine_formal_prager_synge"] is False
