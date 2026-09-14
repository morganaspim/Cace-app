from cace_studio.modules.production_v275 import *
from cace_studio.core.module import ExecutionContext

def test_production_v275():
    m=ProductionV275()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v275"))
    r=out["result"]
    assert r.get("pass",True) is not False
