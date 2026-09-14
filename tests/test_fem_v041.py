from cace_studio.modules.fem_v041 import parameter_sweep
def test_v041_sweep():
 r=parameter_sweep(); assert r['all_certified'] and len(r['sha256'])==64
