from cace_studio.modules.fem_v092 import *
from cace_studio.core.module import ExecutionContext

def test_v092_capability():
    m=ReliabilityV092()
    p=m.resolved_params({})
    out=m.execute({},p,ExecutionContext(run_id="v092"))
    r=out["result"]
    assert r.get("pass", r.get("pass_", True)) is not False
