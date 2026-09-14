from cace_studio.modules.fem_v066 import parallel_determinism
def test_v066():
 r=parallel_determinism(); assert r['pass'] and r['count']==32
