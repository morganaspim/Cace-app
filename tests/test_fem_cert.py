import json, math, numpy as np, pytest
from cace_studio.app import build_registry
from cace_studio.core.graph import Experiment,Node,Edge
from cace_studio.core.executor import GraphExecutor
from cace_studio.core.serialization import load_experiment


def test_v04_certified_discrete_pipeline():
    r=GraphExecutor(build_registry()).run(load_experiment('examples/certified_poisson_v04.cace'))
    assert r.all_verifiers_passed
    c=r.outputs['ires']['residual_certificate']
    assert c['residual_inf_interval'][0] <= 0 <= c['residual_inf_interval'][1]
    assert c['residual_inf_interval'][1] < 1e-14
    assert c['residual_l2_interval'][0] >= 0.0
    e=r.outputs['aerr']['algebraic_error_certificate']
    assert e['certified'] is True
    assert e['gershgorin_lambda_min_lower'] > 0
    assert e['energy_error_upper'] < 1e-13
    gate=r.outputs['gate']['reliability_status']
    assert gate['continuum_error_certified'] is False
    assert r.verification['gate'][0].state.value == 'not-run'


def test_interval_residual_contains_direct_binary64_residual():
    r=GraphExecutor(build_registry()).run(load_experiment('examples/certified_poisson_v04.cace'))
    s=r.outputs['assemble']['system']; u=np.asarray(r.outputs['solve']['solution']['interior'])
    A=np.zeros(s['matrix']['shape'])
    csr=s['matrix']
    for i in range(A.shape[0]):
        for p in range(csr['indptr'][i],csr['indptr'][i+1]): A[i,csr['indices'][p]]=csr['data'][p]
    direct=A@u-np.asarray(s['rhs'])
    rows=r.outputs['ires']['residual_certificate']['row_intervals']
    assert all(lo <= x <= hi for (lo,hi),x in zip(rows,direct))


def test_variable_spd_tensor_and_affine_source_assemble():
    V='[[0,0],[1,0],[1,1],[0,1],[0.5,0.5]]'; E='[[0,1,4],[1,2,4],[2,3,4],[3,0,4]]'
    exp=Experiment(nodes=[
        Node('m','fem_nd.mesh',{'vertices':V,'elements':E}),Node('p','fem_nd.p1_space',{}),
        Node('a','fem_cert.poisson_assemble',{'diffusion':'[[2.0,0.25],[0.25,1.5]]','source_constant':1.0,'source_linear':'[0.5,-0.25]'})],
        edges=[Edge('m','mesh','p','mesh'),Edge('m','mesh','a','mesh'),Edge('p','space','a','space')])
    r=GraphExecutor(build_registry()).run(exp)
    assert r.all_verifiers_passed
    assert r.outputs['a']['problem']['cell_coercivity_lower'] > 1.0
    assert r.verification['a'][0].metrics['matrix_min_eigenvalue'] > 0


def test_non_spd_diffusion_rejected():
    V='[[0,0],[1,0],[1,1],[0,1],[0.5,0.5]]'; E='[[0,1,4],[1,2,4],[2,3,4],[3,0,4]]'
    exp=Experiment(nodes=[Node('m','fem_nd.mesh',{'vertices':V,'elements':E}),Node('p','fem_nd.p1_space',{}),Node('a','fem_cert.poisson_assemble',{'diffusion':'[[1,2],[2,1]]'})],edges=[Edge('m','mesh','p','mesh'),Edge('m','mesh','a','mesh'),Edge('p','space','a','space')])
    with pytest.raises(Exception): GraphExecutor(build_registry()).run(exp)


def test_interval_ldlt_can_certify_when_gershgorin_is_too_weak():
    # SPD but first Gershgorin lower is negative. v0.5 falls back to interval LDL^T.
    sys={'matrix':{'shape':[2,2],'data':[1.0,1.1,1.1,2.0],'indices':[0,1,0,1],'indptr':[0,2,4]},'rhs':[0.,0.],'interior_dofs':[0,1],'boundary_dofs':[],'full_dofs':2}
    sol={'values':[0.,0.],'interior':[0.,0.]}
    exp=Experiment(nodes=[Node('r','fem_cert.interval_residual',{}),Node('e','fem_cert.discrete_energy_error',{})],edges=[Edge('r','residual_certificate','e','residual_certificate')])
    rr=GraphExecutor(build_registry()).run(exp,external_inputs={'r':{'system':sys,'solution':sol},'e':{'system':sys}})
    c=rr.outputs['e']['algebraic_error_certificate']
    assert c['certified'] is True
    assert c['coercivity_method']=='interval-ldlt'

def test_spd_certificate_refuses_indefinite_matrix():
    sys={'matrix':{'shape':[2,2],'data':[1.0,2.0,2.0,1.0],'indices':[0,1,0,1],'indptr':[0,2,4]},'rhs':[0.,0.],'interior_dofs':[0,1],'boundary_dofs':[],'full_dofs':2}
    sol={'values':[0.,0.],'interior':[0.,0.]}
    exp=Experiment(nodes=[Node('r','fem_cert.interval_residual',{}),Node('e','fem_cert.discrete_energy_error',{})],edges=[Edge('r','residual_certificate','e','residual_certificate')])
    rr=GraphExecutor(build_registry()).run(exp,external_inputs={'r':{'system':sys,'solution':sol},'e':{'system':sys}})
    assert rr.outputs['e']['algebraic_error_certificate']['certified'] is False
    assert rr.verification['e'][0].state.value == 'not-run'


def test_cpu_gpu_equivalence_is_pass_or_not_run():
    r=GraphExecutor(build_registry()).run(load_experiment('examples/certified_poisson_v04.cace'))
    rec=r.verification['equiv'][0]
    assert rec.state.value in ('pass','not-run')
    if rec.state.value=='pass': assert r.outputs['equiv']['equivalence']['max_abs_difference'] <= r.outputs['equiv']['equivalence']['tolerance']

def test_graph_certificate_distinguishes_not_run_from_failure():
    from cace_studio.core.report import graph_certificate
    r=GraphExecutor(build_registry()).run(load_experiment('examples/certified_poisson_v04.cace'))
    g=graph_certificate(r)
    assert g['failed_verifiers'] == 0
    assert g['not_run_verifiers'] >= 1
    assert g['all_verifiers_passed'] is True
