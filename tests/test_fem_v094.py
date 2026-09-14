from cace_studio.modules.fem_v094 import *
from cace_studio.core.module import ExecutionContext

def test_v094_capability():
    m=ReliabilityV094()
    p=m.resolved_params({})
    out=m.execute({},p,ExecutionContext(run_id="v094"))
    r=out["result"]
    assert r.get("pass", r.get("pass_", True)) is not False
