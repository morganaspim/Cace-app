from cace_studio.modules.fem_v078 import *
from cace_studio.core.module import ExecutionContext

def test_v078_capability():
    m=ReliabilityV078()
    p=m.resolved_params({})
    out=m.execute({},p,ExecutionContext(run_id="v078"))
    r=out["result"]
    assert r.get("pass", r.get("pass_", True)) is not False
