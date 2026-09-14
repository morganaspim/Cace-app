from copy import deepcopy
import numpy as np
from cace_studio.core.formal_kernel_v15 import assembly_artifact,check_artifact
from cace_studio.core.formal_bridge_v15 import invoke_assembly_checker
from cace_studio.modules.fem_v015 import _interval_ldlt,FormalRegistryBridgeV15
from cace_studio.core.module import ExecutionContext
from cace_studio.app import build_registry
from cace_studio.core.graph import Experiment,Node,Edge
from cace_studio.core.executor import GraphExecutor
from cace_studio.core.report import run_report

def ctx(): return ExecutionContext(run_id='test-v015')

def test_exact_global_assembly_invariants_are_machine_checked():
    r=check_artifact(assembly_artifact())
    assert r['passed']
    assert set(r['claims_checked'])=={'local-row-sum-zero','global-symmetry','global-constant-nullspace','dirichlet-reduction-spd'}
    assert all(float(__import__('fractions').Fraction(v))>0 for v in r['ldlt_pivots'])

def test_tampered_mesh_is_rejected():
    a=deepcopy(assembly_artifact()); a['nodes'][2]=a['nodes'][1]
    assert not check_artifact(a)['passed']

def test_subprocess_checker_v15_is_real():
    r=invoke_assembly_checker(assembly_artifact()); assert r['passed'] and r['process_returncode']==0

def test_registry_rechecks_forged_attestation():
    bad=assembly_artifact(); bad['nodes'][2]=bad['nodes'][1]
    fake={'artifact':bad,'attestation':{'passed':True},'machine_checked':True}
    out=FormalRegistryBridgeV15().execute({'formal_result':fake},{},ctx())
    assert out['theorem']['status']=='obligation-only' and not out['theorem']['formal_evidence']

def test_interval_ldlt_certifies_spd_and_reconstructs():
    A=np.array([[4.,-1.,0.],[-1.,4.,-1.],[0.,-1.,3.]])
    c=_interval_ldlt(A); assert c['certified'] and c['min_pivot_lower']>0 and c['max_reconstruction_width']>=0

def test_interval_ldlt_refuses_indefinite_matrix():
    c=_interval_ldlt(np.array([[1.,2.],[2.,1.]])); assert not c['certified']

def test_full_v015_graph_composes_formal_and_interval_evidence():
    nodes=[Node('proof','formal15.assembly_invariants',{}),Node('bridge','formal15.registry_bridge',{}),
           Node('mesh','fem_nd.mesh',{'vertices':'[[0,0],[2,0],[2,1],[0,1],[1,0.5]]','elements':'[[0,1,4],[1,2,4],[2,3,4],[3,0,4]]'}),
           Node('space','fem_nd.p1_space',{}),Node('assemble','fem_cert.poisson_assemble',{'diffusion':'[[1.5,0.1],[0.1,1.0]]','source_constant':1.0,'source_linear':'[0.25,-0.1]'}),
           Node('fac','fem15.verified_ldlt',{}),Node('sum','fem15.summary',{})]
    edges=[Edge('proof','formal_result','bridge','formal_result'),Edge('mesh','mesh','space','mesh'),Edge('mesh','mesh','assemble','mesh'),Edge('space','space','assemble','space'),Edge('assemble','system','fac','system'),Edge('bridge','theorem','sum','theorem'),Edge('fac','factorization_certificate','sum','factorization_certificate')]
    exp=Experiment(name='v015 assembly factorization',nodes=nodes,edges=edges)
    run=GraphExecutor(build_registry()).run(exp); rep=run_report(run,exp.name)
    assert run.all_verifiers_passed
    assert {'formally-verified','interval-certified'}.issubset(set(rep['graph_certificate']['evidence_generated']))
    assert run.outputs['sum']['summary']['continuum_pde_formally_verified'] is False
