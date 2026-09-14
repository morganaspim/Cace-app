from cace_studio.modules.fem_v047 import scaling_3d
def test_v047_3d_scaling():
 r=scaling_3d(); assert r['all_certified'] and r['dimensions_increasing']
