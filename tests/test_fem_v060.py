from cace_studio.modules.fem_v060 import monotonicity_audit
def test_v060():
 r=monotonicity_audit(); assert r['pass'] and not r['violations']
