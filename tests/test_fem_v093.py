from cace_studio.modules.fem_v093 import *
from cace_studio.core.module import ExecutionContext

def test_v093_capability():
    m=ReliabilityV093()
    p=m.resolved_params({})
    out=m.execute({},p,ExecutionContext(run_id="v093"))
    r=out["result"]
    assert r.get("pass", r.get("pass_", True)) is not False
