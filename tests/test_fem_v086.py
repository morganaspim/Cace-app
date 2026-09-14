from cace_studio.modules.fem_v086 import *
from cace_studio.core.module import ExecutionContext

def test_v086_capability():
    m=ReliabilityV086()
    p=m.resolved_params({})
    out=m.execute({},p,ExecutionContext(run_id="v086"))
    r=out["result"]
    assert r.get("pass", r.get("pass_", True)) is not False
    assert r["closed"] is False
