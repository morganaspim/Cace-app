from cace_studio.modules.fem_v035 import consolidated_v035
def test_v035_consolidated():
 r=consolidated_v035(); assert r['all_checks_pass']; assert not r['evidence_boundary']['formal_continuum_pde']
