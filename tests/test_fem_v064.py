from cace_studio.modules.fem_v064 import solve_residual_witness
def test_v064():
 r=solve_residual_witness(); assert r['pass'] and r['residual_inf']<1e-13
