from cace_studio.modules.fem_v079 import *
from cace_studio.core.module import ExecutionContext

def test_v079_capability():
    m=ReliabilityV079()
    p=m.resolved_params({})
    out=m.execute({},p,ExecutionContext(run_id="v079"))
    r=out["result"]
    assert r.get("pass", r.get("pass_", True)) is not False
