from cace_studio.modules.fem_v053 import interval_dot
def test_v053():
 r=interval_dot(); assert r['pass'] and r['lower']<=r['exact_float']<=r['upper'] and r['width']>0
