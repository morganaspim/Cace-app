from cace_studio.modules.fem_v090 import *
from cace_studio.core.module import ExecutionContext

def test_v090_capability():
    m=ReliabilityV090()
    p=m.resolved_params({})
    out=m.execute({},p,ExecutionContext(run_id="v090"))
    r=out["result"]
    assert r.get("pass", r.get("pass_", True)) is not False
