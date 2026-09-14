from cace_studio.modules.formal_v301 import *
from cace_studio.core.module import ExecutionContext

def test_formal_v301():
    m=FormalV301()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v301"))
    r=out["result"]
    assert r.get("pass",True) is not False
    assert r["pin"]["mathlib"] == "v4.32.1"
    assert r["formal_status"] in ("NOT_RUN","READY")
