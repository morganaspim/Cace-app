from cace_studio.modules.fem_v075 import milestone_v075
def test_v075():
 r=milestone_v075(); assert r['pass'] and r['release']=='0.75.0' and len(r['sha256'])==64 and not any(r['summary']['boundaries'].values())
