from cace_studio.modules.fem_v039 import operator_health
def test_v039_health():
 r=operator_health(); assert r['positive_diagonal'] and r['exact_spd_certificate'] and r['min_exact_pivot']>0
