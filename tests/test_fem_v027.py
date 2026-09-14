from cace_studio.modules.fem_v027 import mixed_precision_refinement
def test_v027_refines():
 r=mixed_precision_refinement(6,6,2); assert r['improved'] and r['final_residual']<=1e-9 and r['exact_structure_certified']
