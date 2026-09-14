from cace_studio.modules.fem_v062 import uncertainty_budget
def test_v062():
 r=uncertainty_budget(); assert r['pass'] and r['worst_case']<=r['limit']; assert not uncertainty_budget({'x':0.1},0.05)['pass']
