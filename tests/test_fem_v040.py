from cace_studio.modules.fem_v040 import compensated_reduction_audit
def test_v040_reduction():
 r=compensated_reduction_audit(); assert r['neumaier_error']==0; assert r['naive_error']>0
