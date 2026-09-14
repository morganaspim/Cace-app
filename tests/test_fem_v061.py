from cace_studio.modules.fem_v061 import ensemble_consensus
def test_v061():
 r=ensemble_consensus(); assert r['pass']; assert not ensemble_consensus((1,1.1),1e-3)['pass']
