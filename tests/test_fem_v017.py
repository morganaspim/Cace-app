from cace_studio.modules.fem_v017 import structured_square_p1_csr,minimum_degree_ordering,symbolic_elimination,sparse_exact_ldlt,ordering_benchmark
from cace_studio.app import build_registry
from cace_studio.core.graph import Experiment,Node,Edge
from cace_studio.core.executor import GraphExecutor
from cace_studio.core.report import run_report


def test_min_degree_is_deterministic_permutation_and_reduces_fill_on_2d_fem():
    csr=structured_square_p1_csr(10,10)
    a=minimum_degree_ordering(csr);b=minimum_degree_ordering(csr)
    assert a==b and sorted(a)==list(range(csr['shape'][0]))
    nat=symbolic_elimination(csr); md=symbolic_elimination(csr,a)
    assert md['fill_edges'] < nat['fill_edges']


def test_exact_reordered_sparse_ldlt_matches_symbolic_fill_without_dense_materialization():
    csr=structured_square_p1_csr(8,8); order=minimum_degree_ordering(csr); sym=symbolic_elimination(csr,order); fac=sparse_exact_ldlt(csr,order)
    assert fac['certified'] and fac['exact_reconstruction'] and fac['dense_materialization'] is False
    assert fac['factor_nnz']==sym['factor_nnz']
    assert fac['fill_entries']==sym['fill_edges']


def test_larger_2d_sparse_benchmark_scales_and_ordering_is_useful():
    csr=structured_square_p1_csr(14,14) # 169 interior DOFs
    b=ordering_benchmark(csr)
    assert b['dimension']==169 and b['factorization']['certified']
    assert b['minimum_degree']['fill_edges'] < b['natural']['fill_edges']
    assert b['factorization']['factor_nnz'] < b['natural']['factor_nnz']


def test_v017_graph():
    exp=Experiment(name='v017 sparse ordering',nodes=[Node('bench','fem17.ordering_benchmark',{'nx':8,'ny':8}),Node('sum','fem17.summary',{})],edges=[Edge('bench','benchmark','sum','benchmark')])
    run=GraphExecutor(build_registry()).run(exp); rep=run_report(run,exp.name)
    assert run.all_verifiers_passed
    s=run.outputs['sum']['summary']; assert s['exact_reconstruction'] and not s['dense_materialization']
    assert 'symbolic' in rep['graph_certificate']['evidence_generated']

def test_adaptive_2d_irregular_mesh_fill_reduction():
    import json
    from cace_studio.core.module import ExecutionContext
    from cace_studio.modules.fem_nd import SimplexMeshND,_assemble,_csr_from_dense
    from cace_studio.modules.fem_v011 import CertifiedAdaptiveSolveLoop2D
    ctx=ExecutionContext(run_id='v017-adaptive')
    p={'vertices':json.dumps([[0,0],[1,0],[1,1],[0,1],[.5,.5]]),'elements':json.dumps([[0,1,4],[1,2,4],[2,3,4],[3,0,4]])}
    mesh=SimplexMeshND().execute({},p,ctx)['mesh']
    out=CertifiedAdaptiveSolveLoop2D().execute({'mesh':mesh},{'source':1.0,'theta':0.5,'max_iterations':4,'stop_mode':'estimator_upper','tolerance':0.0},ctx)
    _,_,Ar,_,interior,_,_=_assemble(out['final_mesh'],1.0); csr=_csr_from_dense(Ar); b=ordering_benchmark(csr)
    assert len(interior)==28
    assert b['minimum_degree']['fill_edges'] < b['natural']['fill_edges']
    assert b['factorization']['certified']

def test_v017_example_visualization_exists_and_is_png():
    from pathlib import Path
    p=Path('examples/v17_fill_pattern.png')
    assert p.exists() and p.stat().st_size>1000 and p.read_bytes()[:8]==b'\x89PNG\r\n\x1a\n'

def test_native_sparse_ldlt_structure_matches_exact_verifier():
    from cace_studio.core.native_runtime import NativeRuntime
    csr=structured_square_p1_csr(8,8);order=minimum_degree_ordering(csr);exact=sparse_exact_ldlt(csr,order);native=NativeRuntime().sparse_ldlt_stats(csr,order)
    assert native['factor_nnz']==exact['factor_nnz'] and native['fill_edges']==exact['fill_entries'] and native['min_pivot']>0
