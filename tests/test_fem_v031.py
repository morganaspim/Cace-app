from cace_studio.modules.fem_v031 import structured_3d_poisson_csr, stress_3d
def test_v031_shape():
 a=structured_3d_poisson_csr(4); assert a['shape']==[27,27]
def test_v031_exact_stress():
 r=stress_3d(4); assert r['certified'] and r['ordered_fill']<=r['natural_fill']
