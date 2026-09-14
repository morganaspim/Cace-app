from cace_studio.modules.fem_v063 import permutation_roundtrip
def test_v063():
 r=permutation_roundtrip(); assert r['pass'] and r['recovered']==[10,20,30,40]
