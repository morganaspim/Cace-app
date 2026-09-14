import os
import numpy as np
from cace_studio.core.native_runtime import NativeRuntime
from cace_studio.modules.fem_v016 import _python_p1_1d_reduced,sparse_interval_ldlt
from cace_studio.app import build_registry
from cace_studio.core.graph import Experiment,Node,Edge
from cace_studio.core.executor import GraphExecutor
from cace_studio.core.report import run_report


def test_native_v016_runtime_and_p1_assembly(monkeypatch):
    # CMake build output is discoverable by NativeRuntime from repository root.
    rt=NativeRuntime(); assert rt.status.available and tuple(map(int,rt.status.version.split('.'))) >= (0,16,0)
    nodes=[0.,0.2,0.55,0.8,1.0]
    native=rt.p1_1d_stiffness(nodes); py=_python_p1_1d_reduced(nodes)
    assert native['shape']==py['shape'] and native['indices']==py['indices'] and native['indptr']==py['indptr']
    assert np.allclose(native['data'],py['data'],rtol=0,atol=1e-14)


def test_sparse_interval_ldlt_large_tridiagonal_without_dense_materialization():
    nodes=np.linspace(0,1,102).tolist() # 100 interior DOFs
    csr=_python_p1_1d_reduced(nodes)
    c=sparse_interval_ldlt(csr)
    assert c['certified'] and c['dimension']==100 and c['dense_materialization'] is False
    assert c['factor_nnz'] < 4*c['dimension']
    assert c['fill_entries']==0
    assert c['min_pivot_lower']>0


def test_sparse_interval_ldlt_rejects_indefinite_sparse_matrix():
    csr={'shape':[2,2],'data':[1.,2.,2.,1.],'indices':[0,1,0,1],'indptr':[0,2,4]}
    assert not sparse_interval_ldlt(csr)['certified']


def test_v016_graph_composes_native_and_sparse_certificate():
    nodes=[Node('native','runtime16.native_p1_assembly',{'nodes':'[0,0.2,0.55,0.8,1.0]'}),Node('fac','fem16.sparse_verified_ldlt',{}),Node('sum','fem16.summary',{})]
    edges=[Edge('native','system','fac','system'),Edge('native','equivalence','sum','equivalence'),Edge('fac','factorization_certificate','sum','factorization_certificate')]
    exp=Experiment(name='v016 native sparse',nodes=nodes,edges=edges)
    run=GraphExecutor(build_registry()).run(exp); rep=run_report(run,exp.name)
    assert run.all_verifiers_passed
    s=run.outputs['sum']['summary']; assert s['native_assembly_equivalent'] and s['sparse_factorization_certified'] and s['dense_materialization'] is False
    assert {'numerical','symbolic'}.issubset(set(rep['graph_certificate']['evidence_generated']))
