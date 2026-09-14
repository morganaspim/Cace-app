import math
from pathlib import Path
from cace_studio.core.module import ExecutionContext, ValidationError
from cace_studio.modules.fem_nd import SimplexMeshND,P1SimplexSpaceND,LinearSolverND
from cace_studio.modules.fem_cert import CertifiedPoissonAssembly
from cace_studio.modules.fem_cert2d import CertifiedShapeRegularity2D
from cace_studio.modules.fem_cert2d_general import CertifiedDiffusion2D
from cace_studio.modules.fem_cert2d_v08 import ComputedEnergyNorm2D
from cace_studio.modules.fem_v09 import *
CTX=ExecutionContext(run_id='v09-test')
def run(m,inputs=None,params=None):
    inputs=inputs or {}; p=m.resolved_params(params or {}); m.validate(inputs,p); o=m.execute(inputs,p,CTX); return o,m.verify(inputs,p,o,CTX)

def pipeline(tmp_path=None):
    vertices='[[0,0],[2,0],[2,1],[0,1],[1,0.5]]'
    elements='[[0,1,4],[1,2,4],[2,3,4],[3,0,4]]'
    M,_=run(SimplexMeshND(),params={'vertices':vertices,'elements':elements}); mesh=M['mesh']
    sp,_=run(P1SimplexSpaceND(),{'mesh':mesh})
    geo,grec=run(GeneralTriangleGeometry2D(),{'mesh':mesh})
    shape,_=run(CertifiedShapeRegularity2D(),{'geometry_certificate':geo['geometry_certificate']},{'max_ratio':20.0})
    diff,_=run(CertifiedDiffusion2D(),params={'tensor':'[[1.5,0.1],[0.1,1.0]]'})
    ia,_=run(GeneralIntervalAssembly2D(),{'mesh':mesh,'diffusion_certificate':diff['diffusion_certificate']})
    asm,_=run(CertifiedPoissonAssembly(),{'mesh':mesh,'space':sp['space']},{'diffusion':'[[1.5,0.1],[0.1,1.0]]','source_constant':1.0,'source_linear':'[0.25,-0.1]'})
    sol,_=run(LinearSolverND(),{'system':asm['system']})
    src,_=run(GeneralAffineSourceNorm2D(),{'mesh':mesh},{'c':1.0,'lx':0.25,'ly':-0.1})
    pc,_=run(StripPoincare2D(),{'mesh':mesh})
    stab,_=run(GeneralStabilityBound2D(),{'source_norm_certificate':src['source_norm_certificate'],'poincare_certificate':pc['poincare_certificate'],'diffusion_certificate':diff['diffusion_certificate']})
    ce,_=run(ComputedEnergyNorm2D(),{'interval_system':ia['interval_system'],'solution':sol['solution']})
    env,_=run(GeneralErrorEnvelope2D(),{'stability_certificate':stab['stability_certificate'],'computed_energy_certificate':ce['computed_energy_certificate']})
    est,_=run(GeneralResidualEstimatorAffine2D(),{'mesh':mesh,'solution':sol['solution'],'diffusion_certificate':diff['diffusion_certificate']},{'c':1.0,'lx':0.25,'ly':-0.1})
    rel,rrec=run(RunReliabilityEnvelope2D(),{'error_envelope':env['error_envelope'],'estimator_certificate':est['estimator_certificate']},{'max_C_rel':100.0})
    return locals()

def test_general_non_reference_mesh_pipeline():
    p=pipeline(); assert p['geo']['geometry_certificate']['domain_class']=='general-triangular-mesh'; assert p['grec'][0].state.value=='pass'
    assert p['env']['error_envelope']['certified']; assert p['est']['estimator_certificate']['certified']; assert p['rel']['reliability_certificate']['certified']

def test_strip_poincare_uses_shorter_width():
    p=pipeline(); c=p['pc']['poincare_certificate']; assert math.isclose(c['selected_width_upper'],1.0,rel_tol=0,abs_tol=1e-15); assert c['C_p_upper']>=1/math.pi

def test_general_source_norm_and_estimator_positive():
    p=pipeline(); assert p['src']['source_norm_certificate']['l2_norm_interval'][0]>0; assert p['est']['estimator_certificate']['eta_interval'][0]>0

def test_run_reliability_is_explicitly_not_formal():
    p=pipeline(); c=p['rel']['reliability_certificate']; assert c['scope']=='run-specific-general-mesh' and c['formal_evidence'] is False and c['C_rel_run_upper']>0

def test_theorem_registry_v2_preserves_uniform_obligation():
    o,recs=run(TheoremRegistryV2()); r=o['registry']; assert r['schema_version']==2
    uni=[t for t in r['theorems'] if t['theorem_id']==THEOREM_UNIFORM_ID][0]
    assert uni['status']=='obligation-only' and uni['formal_evidence'] is False and len(uni['premises'])>=4
    x,xr=run(GenericReliabilityObligationV09()); assert xr[0].state.value=='not-run'

def test_general_geometry_rejects_clockwise_cell():
    M,_=run(SimplexMeshND(),params={'vertices':'[[0,0],[1,0],[0,1]]','elements':'[[0,2,1]]'})
    try: run(GeneralTriangleGeometry2D(),{'mesh':M['mesh']}); assert False
    except ValidationError: pass

def test_v09_estimator_heatmap_png(tmp_path):
    p=pipeline(); out=tmp_path/'eta.png'; o,recs=run(EstimatorHeatmap2D(),{'mesh':p['mesh'],'estimator_certificate':p['est']['estimator_certificate']},{'output_path':str(out)})
    assert out.exists() and out.stat().st_size>1000 and out.read_bytes()[:8]==b'\x89PNG\r\n\x1a\n'; assert recs[0].state.value=='pass'
