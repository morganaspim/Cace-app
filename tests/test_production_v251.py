from cace_studio.modules.production_v251 import *
from cace_studio.core.module import ExecutionContext

def test_production_v251():
    m=ProductionV251()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v251"))
    r=out["result"]
    assert r.get("pass",True) is not False
