import json,subprocess,sys
from copy import deepcopy
from cace_studio.core.formal_kernel_v14 import affine_artifact,global_spd_artifact,poisson_energy_artifact,check_artifact,KERNEL_NAME
from cace_studio.core.formal_bridge_v14 import invoke_fem_checker
from cace_studio.modules.fem_v014 import FormalRegistryBridgeV14
from cace_studio.core.module import ExecutionContext
from cace_studio.app import build_registry
from cace_studio.core.graph import Experiment,Node,Edge
from cace_studio.core.executor import GraphExecutor
from cace_studio.core.report import run_report

def ctx(): return ExecutionContext(run_id='test-v014')

def test_affine_transform_gradient_and_local_psd_are_exactly_checked_1d_2d_3d():
    for d in (1,2,3):
        r=check_artifact(affine_artifact(d))
        assert r['passed'] and r['checker']==KERNEL_NAME
        assert set(r['claims_checked'])=={'affine-inverse','p1-gradient-transform','local-stiffness-symmetric-psd'}

def test_1d_dirichlet_global_stiffness_spd_identity_is_checked():
    r=check_artifact(global_spd_artifact())
    assert r['passed'] and r['claims_checked']==['global-dirichlet-stiffness-spd']

def test_1d_poisson_energy_identity_is_exactly_checked():
    r=check_artifact(poisson_energy_artifact())
    assert r['passed']
    assert r['global_error_sq']=='1537/235200'
    assert r['claims_checked']==['poisson1d-local-energy-identity','poisson1d-global-energy-identity']

def test_tampered_affine_simplex_is_rejected():
    a=deepcopy(affine_artifact(2)); a['vertices'][2]=a['vertices'][1]
    r=check_artifact(a)
    assert not r['passed'] and any('singular' in e for e in r['errors'])

def test_tampered_poisson_claim_set_is_rejected():
    a=poisson_energy_artifact(); a['claims']=['poisson1d-global-energy-identity']
    assert not check_artifact(a)['passed']

def test_subprocess_checker_v14_is_real():
    r=invoke_fem_checker(affine_artifact(3))
    assert r['passed'] and r['process_returncode']==0 and r['invocation']=='subprocess'

def test_registry_rechecks_and_rejects_forged_v14_attestation():
    bad=affine_artifact(2); bad['vertices'][1]=bad['vertices'][0]
    fake={'artifact':bad,'attestation':{'passed':True},'machine_checked':True}
    out=FormalRegistryBridgeV14().execute({'formal_result':fake},{},ctx())
    assert out['theorem']['status']=='obligation-only' and not out['theorem']['formal_evidence']

def test_full_v014_graph_emits_formal_evidence_without_general_pde_escalation():
    nodes=[Node('a','formal14.affine_simplex',{'dimension':2}),Node('s','formal14.dirichlet_spd_1d',{}),Node('e','formal14.poisson1d_energy',{}),
           Node('ab','formal14.registry_bridge',{}),Node('sb','formal14.registry_bridge',{}),Node('eb','formal14.registry_bridge',{}),Node('sum','formal14.summary',{})]
    edges=[Edge('a','formal_result','ab','formal_result'),Edge('s','formal_result','sb','formal_result'),Edge('e','formal_result','eb','formal_result'),
           Edge('ab','theorem','sum','affine'),Edge('sb','theorem','sum','spd'),Edge('eb','theorem','sum','energy')]
    exp=Experiment(name='v014 formal FEM chain',nodes=nodes,edges=edges)
    run=GraphExecutor(build_registry()).run(exp); report=run_report(run,exp.name)
    assert run.all_verifiers_passed and 'formally-verified' in report['graph_certificate']['evidence_generated']
    assert run.outputs['sum']['summary']['general_2d_reliability_formally_verified'] is False
