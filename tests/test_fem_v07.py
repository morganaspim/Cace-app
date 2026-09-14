import json
import pytest
from cace_studio.core.module import ExecutionContext, ValidationError
from cace_studio.modules.fem_nd import SimplexMeshND, P1SimplexSpaceND, LinearSolverND
from cace_studio.modules.fem_cert import CertifiedPoissonAssembly
from cace_studio.modules.fem_cert2d import CertifiedTriangleGeometry2D, CertifiedShapeRegularity2D, BubblePoissonProblem2D, BubbleContinuumEnergyCertificate2D, BubbleResidualEstimatorCertificate2D
from cace_studio.modules.fem_cert2d_general import CertifiedDiffusion2D, IntervalGlobalAssembly2D, TheoremRegistry2D, ReusableReliabilityGate2D, GenericReliabilityObligationV07, THEOREM_ID

CTX=ExecutionContext(run_id='v07-test')
def run(m, inputs=None, params=None):
    inputs=inputs or {}; p=m.resolved_params(params or {}); m.validate(inputs,p); o=m.execute(inputs,p,CTX); return o,m.verify(inputs,p,o,CTX)

def mesh():
    o,_=run(SimplexMeshND(),params={'vertices':'[[0,0],[1,0],[0,1],[0.3333333333333333,0.3333333333333333]]','elements':'[[0,1,3],[1,2,3],[2,0,3]]'})
    return o['mesh']

def pipeline():
    M=mesh(); sp,_=run(P1SimplexSpaceND(),{'mesh':M}); geo,_=run(CertifiedTriangleGeometry2D(),{'mesh':M}); sh,_=run(CertifiedShapeRegularity2D(),{'geometry_certificate':geo['geometry_certificate']},{'max_ratio':20});
    diff,_=run(CertifiedDiffusion2D(),params={'tensor':'[[1,0],[0,1]]'}); ia,_=run(IntervalGlobalAssembly2D(),{'mesh':M,'geometry_certificate':geo['geometry_certificate'],'diffusion_certificate':diff['diffusion_certificate']})
    prob,_=run(BubblePoissonProblem2D()); asm,_=run(CertifiedPoissonAssembly(),{'mesh':M,'space':sp['space']},{'diffusion':'1.0','source_constant':0.0,'source_linear':'[2.0,2.0]'}); sol,_=run(LinearSolverND(),{'system':asm['system']})
    cont,_=run(BubbleContinuumEnergyCertificate2D(),{'mesh':M,'solution':sol['solution'],'problem':prob['problem'],'geometry_certificate':geo['geometry_certificate']}); est,_=run(BubbleResidualEstimatorCertificate2D(),{'mesh':M,'solution':sol['solution'],'geometry_certificate':geo['geometry_certificate']})
    gate,recs=run(ReusableReliabilityGate2D(),{'shape_certificate':sh['shape_certificate'],'diffusion_certificate':diff['diffusion_certificate'],'continuum_certificate':cont['continuum_certificate'],'estimator_certificate':est['estimator_certificate']},{'C_rel':1.0})
    return diff,ia,gate,recs

def test_diffusion_spd_and_coercivity():
    d,_,_,_=pipeline(); assert d['diffusion_certificate']['spd_certified']; assert d['diffusion_certificate']['coercivity_lower_interval'][0] > 0

def test_interval_global_assembly_contains_positive_scalar_system():
    _,a,_,_=pipeline(); A=a['interval_system']['matrix_intervals']; assert len(A)==1 and A[0][0][0] > 0 and A[0][0][0] <= A[0][0][1]

def test_reusable_theorem_gate_passes_without_formal_claim():
    _,_,g,recs=pipeline(); c=g['theorem_certificate']; assert c['certified'] and c['theorem_id']==THEOREM_ID; assert c['formal_evidence'] is False; assert recs[0].state.value=='pass'

def test_bad_diffusion_rejected():
    m=CertifiedDiffusion2D(); p=m.resolved_params({'tensor':'[[1,2],[2,1]]'})
    with pytest.raises(ValidationError): m.execute({},p,CTX)

def test_registry_keeps_generic_theorem_as_obligation():
    o,_=run(TheoremRegistry2D()); items={x['theorem_id']:x for x in o['registry']['theorems']}; assert items['poisson2d-p1-residual-reliability-shape-regular-v0.7']['status']=='obligation-only'
    f,recs=run(GenericReliabilityObligationV07()); assert not f['theorem_artifact']['machine_checked']; assert recs[0].state.value=='not-run'

def test_gate_refuses_failed_shape_assumption():
    d,a,g,_=pipeline()
    # Re-run the gate with an otherwise-valid certificate whose shape theorem assumption is explicitly false.
    M=mesh(); sp,_=run(P1SimplexSpaceND(),{'mesh':M}); geo,_=run(CertifiedTriangleGeometry2D(),{'mesh':M})
    sh,_=run(CertifiedShapeRegularity2D(),{'geometry_certificate':geo['geometry_certificate']},{'max_ratio':1.0})
    prob,_=run(BubblePoissonProblem2D()); asm,_=run(CertifiedPoissonAssembly(),{'mesh':M,'space':sp['space']},{'diffusion':'1.0','source_constant':0.0,'source_linear':'[2.0,2.0]'}); sol,_=run(LinearSolverND(),{'system':asm['system']})
    cont,_=run(BubbleContinuumEnergyCertificate2D(),{'mesh':M,'solution':sol['solution'],'problem':prob['problem'],'geometry_certificate':geo['geometry_certificate']}); est,_=run(BubbleResidualEstimatorCertificate2D(),{'mesh':M,'solution':sol['solution'],'geometry_certificate':geo['geometry_certificate']})
    out,recs=run(ReusableReliabilityGate2D(),{'shape_certificate':sh['shape_certificate'],'diffusion_certificate':d['diffusion_certificate'],'continuum_certificate':cont['continuum_certificate'],'estimator_certificate':est['estimator_certificate']},{'C_rel':1.0})
    assert out['theorem_certificate']['certified'] is False
    assert 'shape_regular' in out['theorem_certificate']['assumption_failures']
    assert recs[0].state.value == 'not-run'
