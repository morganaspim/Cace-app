from cace_studio.modules.fem_v020 import v020_benchmark, render_v020_benchmark
from cace_studio.modules.fem_v017 import structured_square_p1_csr, minimum_degree_ordering
from cace_studio.modules.fem_v018 import matvec
from cace_studio.core.native_runtime import NativeRuntime

def test_dense_block_supernodal_matches_oracle():
    b=v020_benchmark(8,8,4,1)
    for k in ('supernodal_single_thread','supernodal_thread_pool'):
        r=b[k]; assert r['structure_matches_exact']; assert r['max_solution_error']<=1e-10; assert r['residual_inf']<=1e-10
    assert b['supernodal_thread_pool']['supernodes']==b['symbolic_supernodes']['count']
    assert b['supernodal_thread_pool']['max_supernode_size']==b['symbolic_supernodes']['max_size']

def test_workspace_reuse_and_thread_pool_instrumentation():
    b=v020_benchmark(9,9,4,1); r=b['supernodal_thread_pool']
    assert r['scheduled_tasks']==r['supernodes']
    assert r['workspace_reallocations'] < r['scheduled_tasks']
    assert r['peak_workspace_entries'] >= r['peak_front_size']**2
    assert r['thread_count']==4

def test_supernodal_refuses_indefinite():
    csr={'shape':[2,2],'data':[1.0,2.0,2.0,1.0],'indices':[0,1,0,1],'indptr':[0,2,4]}
    try: NativeRuntime().sparse_supernodal_ldlt_solve(csr,[0,1],[1.0,1.0],2)
    except RuntimeError: return
    assert False

def test_supernodal_known_solution():
    csr=structured_square_p1_csr(7,7); o=minimum_degree_ordering(csr); x=[1+.02*i for i in range(csr['shape'][0])]; b=matvec(csr,x); r=NativeRuntime().sparse_supernodal_ldlt_solve(csr,o,b,3)
    assert max(abs(a-bb) for a,bb in zip(r['x'],x))<=1e-10

def test_v020_visualization(tmp_path):
    b=v020_benchmark(7,7,3,1); p=tmp_path/'v20.png'; render_v020_benchmark(b,p); raw=p.read_bytes(); assert len(raw)>1000 and raw[:8]==b'\x89PNG\r\n\x1a\n'
