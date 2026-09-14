from cace_studio.modules.fem_v074 import qualification_v074
def test_v074():
 r=qualification_v074(); assert r['pass'] and r['passed']==r['total']==5
