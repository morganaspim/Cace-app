from cace_studio.modules.fem_v030 import multi_rhs_campaign
def test_v030_multi_rhs():
 r=multi_rhs_campaign(6,6,3); assert r['exact_structure_certified']; assert r['max_solution_error']<=1e-10; assert r['max_residual_inf']<=1e-10
