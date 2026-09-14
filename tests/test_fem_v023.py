from cace_studio.modules.fem_v023 import gpu_dense_equivalence

def test_gpu_equivalence_is_explicitly_conditional():
    r=gpu_dense_equivalence(12); assert 'available' in r and r['backend']=='cupy/cuda'
    if r['available']: assert r['max_abs_error']<=1e-10
    else: assert 'reason' in r
