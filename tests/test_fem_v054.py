from cace_studio.modules.fem_v054 import exact_residual_witness
def test_v054():
 r=exact_residual_witness(); assert r['pass'] and r['residual']==['0','0']
