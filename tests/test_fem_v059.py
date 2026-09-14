from cace_studio.modules.fem_v059 import sensitivity_audit
def test_v059():
 r=sensitivity_audit(); assert r['pass'] and r['abs_error']<1e-9
