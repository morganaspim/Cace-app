from copy import deepcopy
from cace_studio.modules.fem_v046 import ledger_fixture,verify_ledger
def test_v046_ledger():
 r=ledger_fixture(); assert r['verified']; t=deepcopy(r['chain']); t[1]['event']['status']='FAIL'; assert not verify_ledger(t)
