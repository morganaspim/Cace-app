from cace_studio.modules.next_v228 import *
from cace_studio.core.module import ExecutionContext

def test_next_v228():
    m=NextV228()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v228"))
    r=out["result"]
    assert r.get("pass",True) is not False
