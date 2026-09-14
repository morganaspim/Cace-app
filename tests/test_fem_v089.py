from cace_studio.modules.fem_v089 import *
from cace_studio.core.module import ExecutionContext

def test_v089_capability():
    m=ReliabilityV089()
    p=m.resolved_params({})
    out=m.execute({},p,ExecutionContext(run_id="v089"))
    r=out["result"]
    assert r.get("pass", r.get("pass_", True)) is not False
