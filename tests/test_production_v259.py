from cace_studio.modules.production_v259 import *
from cace_studio.core.module import ExecutionContext

def test_production_v259():
    m=ProductionV259()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v259"))
    r=out["result"]
    assert r.get("pass",True) is not False
