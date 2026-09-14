from cace_studio.modules.fem_v036 import replay_fingerprint
def test_v036_replay():
 r=replay_fingerprint(); assert r['replay_equal']; assert r['sha256']==r['replay_sha256']
