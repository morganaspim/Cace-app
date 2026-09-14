from cace_studio.modules.fem_v044 import factor_replay
def test_v044_replay():
 r=factor_replay(); assert r['stable'] and r['certified']
