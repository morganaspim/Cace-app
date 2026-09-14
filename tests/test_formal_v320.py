from cace_studio.modules.formal_v320 import *
from cace_studio.core.module import ExecutionContext

def test_formal_v320():
    m=FormalV320()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v320"))
    r=out["result"]
    assert r.get("pass",True) is not False
    assert r["full_machine_formal_discrete_prager_synge"] is False
