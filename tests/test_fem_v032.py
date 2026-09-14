from cace_studio.modules.fem_v032 import portfolio_score
def test_v032_policy():
 r=portfolio_score(7,7,2,1); assert r['selected'] in r['eligible']; assert len(r['eligible'])>=1
