from cace_studio.modules.fem_v097 import *
from cace_studio.core.module import ExecutionContext

def test_v097_capability():
    m=ReliabilityV097()
    p=m.resolved_params({})
    out=m.execute({},p,ExecutionContext(run_id="v097"))
    r=out["result"]
    assert r.get("pass", r.get("pass_", True)) is not False
