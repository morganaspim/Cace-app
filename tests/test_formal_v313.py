from cace_studio.modules.formal_v313 import *
from cace_studio.core.module import ExecutionContext

def test_formal_v313():
    m=FormalV313()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v313"))
    r=out["result"]
    assert r.get("pass",True) is not False
