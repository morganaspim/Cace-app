from cace_studio.modules.fem_v038 import convergence_audit
def test_v038_audit():
 r=convergence_audit(); assert r['all_certified'] and r['dimensions_increasing'] and r['finite_positive_ratios']
