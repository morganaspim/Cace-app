from cace_studio.modules.fem_v087 import *
from cace_studio.core.module import ExecutionContext

def test_v087_capability():
    m=ReliabilityV087()
    p=m.resolved_params({})
    out=m.execute({},p,ExecutionContext(run_id="v087"))
    r=out["result"]
    assert r.get("pass", r.get("pass_", True)) is not False
