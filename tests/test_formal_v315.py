from cace_studio.modules.formal_v315 import *
from cace_studio.core.module import ExecutionContext

def test_formal_v315():
    m=FormalV315()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v315"))
    r=out["result"]
    assert r.get("pass",True) is not False
    assert r["formal_promotion_allowed"] == bool(r["build_attestation"].get("passed"))
