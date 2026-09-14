import json, subprocess, sys
from copy import deepcopy
from pathlib import Path
from cace_studio.core.formal_kernel import canonical_artifact, check_artifact, KERNEL_NAME
from cace_studio.core.formal_bridge import invoke_formal_checker
from cace_studio.core.module import ExecutionContext
from cace_studio.modules.fem_v013 import ReferenceSimplexFormalProof, FormalTheoremRegistryBridge
from cace_studio.app import build_registry
from cace_studio.core.graph import Experiment, Node, Edge
from cace_studio.core.executor import GraphExecutor
from cace_studio.core.report import run_report


def ctx(): return ExecutionContext(run_id='test-v013')

def test_exact_formal_kernel_checks_dimensions_1_2_3():
    for d in (1,2,3):
        r=check_artifact(canonical_artifact(d))
        assert r['passed'] and r['checker']==KERNEL_NAME
        assert r['claims_checked']==['partition-of-unity','kronecker-nodal-identity']

def test_tampered_formal_artifact_is_rejected():
    a=deepcopy(canonical_artifact(2)); a['basis'][0]['coeffs'][1]='-2'
    r=check_artifact(a)
    assert not r['passed'] and r['errors']

def test_subprocess_checker_is_actually_invoked():
    r=invoke_formal_checker(canonical_artifact(3))
    assert r['passed'] and r['process_returncode']==0 and r['invocation']=='subprocess'

def test_cli_checker_rejects_tamper(tmp_path):
    a=canonical_artifact(1); a['claims']=['partition-of-unity']
    p=tmp_path/'bad.json'; p.write_text(json.dumps(a))
    proc=subprocess.run([sys.executable,'-m','cace_studio.formal_checker','--artifact',str(p)],capture_output=True,text=True)
    assert proc.returncode != 0
    assert json.loads(proc.stdout)['passed'] is False

def test_module_emits_formal_evidence_only_after_passed_attestation():
    m=ReferenceSimplexFormalProof(); out=m.execute({}, {'dimension':2}, ctx()); rec=m.verify({}, {'dimension':2}, out, ctx())[0]
    assert rec.passed and rec.kind.value=='formally-verified' and out['formal_result']['machine_checked']

def test_registry_bridge_promotes_only_checked_attestation():
    p=ReferenceSimplexFormalProof().execute({}, {'dimension':2}, ctx())
    m=FormalTheoremRegistryBridge(); out=m.execute({'formal_result':p['formal_result']},{},ctx()); rec=m.verify({}, {}, out, ctx())[0]
    assert out['theorem']['status']=='machine-checked' and out['theorem']['formal_evidence'] is True and rec.passed

def test_graph_certificate_refuses_unregistered_historical_formal_evidence():
    exp=Experiment(name='v013 formal bridge',nodes=[Node('proof','formal13.reference_simplex_barycentric',{'dimension':2}),Node('bridge','formal13.registry_bridge',{}),Node('summary','formal13.summary',{})],edges=[
        Edge('proof','formal_result','bridge','formal_result'),Edge('proof','formal_result','summary','formal_result'),Edge('bridge','theorem','summary','theorem')])
    r=GraphExecutor(build_registry()).run(exp); report=run_report(r,exp.name)
    records=[record for rs in r.verification.values() for record in rs]
    assert not r.all_verifiers_passed
    assert 'formally-verified' not in report['graph_certificate']['evidence_generated']
    assert any(
        record.state.value == 'not-run'
        and record.metrics.get('formal_gate_reason') == 'claim-registry-entry-missing'
        for record in records
    )
    assert r.outputs['summary']['summary']['pde_reliability_formally_verified'] is False


def test_registry_bridge_rejects_forged_upstream_attestation():
    fake_art=canonical_artifact(2); fake_art['basis'][0]['coeffs'][1]='-9'
    fake={'artifact':fake_art,'attestation':{'passed':True,'process_returncode':0},'machine_checked':True}
    m=FormalTheoremRegistryBridge(); out=m.execute({'formal_result':fake},{},ctx())
    assert out['theorem']['status']=='obligation-only'
    assert out['theorem']['formal_evidence'] is False
    assert out['theorem']['promotion_recheck']['passed'] is False
