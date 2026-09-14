from cace_studio.modules.fem_v050 import milestone_v050
def test_v050_milestone():
 r=milestone_v050(); assert r['all_pass']; assert not r['summary']['continuum_formal_promoted']; assert len(r['sha256'])==64
