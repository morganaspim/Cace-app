from cace_studio.modules.fem_v080 import *
from cace_studio.core.module import ExecutionContext

def test_v080_capability():
    m=ReliabilityV080()
    p=m.resolved_params({})
    out=m.execute({},p,ExecutionContext(run_id="v080"))
    r=out["result"]
    assert r.get("pass", r.get("pass_", True)) is not False
