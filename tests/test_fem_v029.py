from cace_studio.modules.fem_v029 import matrix_diagnostics
def test_v029_health():
 r=matrix_diagnostics(7,7); assert r['symmetric'] and r['positive_diagonal'] and r['gershgorin_upper']>0
