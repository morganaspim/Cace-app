from cace_studio.modules.fem_v021 import dense_kernel_benchmark, v021_benchmark

def test_v021_dense_kernel_reference():
    r=dense_kernel_benchmark(24,1); assert r['max_abs_reference_error']<1e-10; assert r['flop_count']==2*24**3

def test_v021_native_chain_still_verified():
    r=v021_benchmark(7,7,2,1,24); n=r['native']['supernodal_thread_pool']; assert n['structure_matches_exact']; assert n['max_solution_error']<1e-10
