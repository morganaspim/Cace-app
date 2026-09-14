from cace_studio.modules.fem_v058 import cache_integrity
def test_v058():
 r=cache_integrity(); assert r['pass'] and r['tamper_rejected'] and len(r['sha256'])==64
