from cace_studio.modules.formal_v319 import *
from cace_studio.core.module import ExecutionContext

def test_formal_v319():
    m=FormalV319()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v319"))
    r=out["result"]
    assert r.get("pass",True) is not False
    assert r["formal_evidence_promotable"] == r["dual_verification_complete"]
