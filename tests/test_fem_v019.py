from cace_studio.modules.fem_v019 import v019_benchmark
from cace_studio.modules.fem_v017 import structured_square_p1_csr, minimum_degree_ordering
from cace_studio.modules.fem_v018 import matvec
from cace_studio.core.native_runtime import NativeRuntime


def test_native_multifrontal_matches_exact_structure_and_solution():
    b=v019_benchmark(8,8,parallel_depth=12,repeats=1)
    assert b['exact_factorization']['certified']
    for key in ('left_looking','multifrontal_sequential','multifrontal_parallel'):
        r=b[key]
        assert r['structure_matches_exact']
        assert r['max_solution_error'] <= 1e-10
        assert r['residual_inf'] <= 1e-10
    assert b['multifrontal_sequential']['peak_front_size'] >= 1
    assert b['multifrontal_sequential']['total_front_entries'] >= b['multifrontal_sequential']['peak_front_size']**2


def test_parallel_subtree_path_actually_spawns_tasks():
    b=v019_benchmark(10,10,parallel_depth=20,repeats=1)
    assert b['multifrontal_parallel']['parallel_tasks'] > 0


def test_multifrontal_refuses_indefinite_system():
    csr={'shape':[2,2],'data':[1.0,2.0,2.0,1.0],'indices':[0,1,0,1],'indptr':[0,2,4]}
    rt=NativeRuntime(); assert rt.status.available
    try:
        rt.sparse_multifrontal_ldlt_solve(csr,[0,1],[1.0,1.0],0)
    except RuntimeError:
        return
    assert False, 'indefinite system should be refused'


def test_multifrontal_known_solution_on_grid():
    csr=structured_square_p1_csr(7,7); order=minimum_degree_ordering(csr)
    x=[1.0+0.02*i for i in range(csr['shape'][0])]; b=matvec(csr,x)
    r=NativeRuntime().sparse_multifrontal_ldlt_solve(csr,order,b,8)
    assert max(abs(a-bb) for a,bb in zip(r['x'],x)) <= 1e-10
    assert r['factor_nnz'] > 0


def test_v019_visualization_from_real_benchmark(tmp_path):
    from cace_studio.modules.fem_v019 import v019_benchmark, render_v019_benchmark
    p=tmp_path/'v19.png'; b=v019_benchmark(7,7,20,1); render_v019_benchmark(b,p)
    raw=p.read_bytes(); assert len(raw)>1000 and raw[:8]==b'\x89PNG\r\n\x1a\n'
