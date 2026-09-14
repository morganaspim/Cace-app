from cace_studio.modules.fem_v085 import *
from cace_studio.core.module import ExecutionContext

def test_v085_capability():
    m=ReliabilityV085()
    p=m.resolved_params({})
    out=m.execute({},p,ExecutionContext(run_id="v085"))
    r=out["result"]
    assert r.get("pass", r.get("pass_", True)) is not False
    assert r["closed"] is False
