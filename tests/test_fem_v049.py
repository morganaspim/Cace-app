from cace_studio.modules.fem_v049 import qualification_matrix
def test_v049_qualification():
 r=qualification_matrix(); assert r['all_pass']; assert all(r['gates'].values())
