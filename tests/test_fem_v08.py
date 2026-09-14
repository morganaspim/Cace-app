import os, math
from pathlib import Path
from cace_studio.core.module import ExecutionContext
from cace_studio.modules.fem_nd import SimplexMeshND,P1SimplexSpaceND,LinearSolverND
from cace_studio.modules.fem_cert import CertifiedPoissonAssembly
from cace_studio.modules.fem_cert2d import CertifiedTriangleGeometry2D,CertifiedShapeRegularity2D
from cace_studio.modules.fem_cert2d_general import CertifiedDiffusion2D,IntervalGlobalAssembly2D
from cace_studio.modules.fem_cert2d_v08 import AffineSourceNorm2D,ReferenceTriangleStability2D,ComputedEnergyNorm2D,ExactSolutionFreeErrorBound2D,FEMVisualization2D
CTX=ExecutionContext(run_id='v08-test')
def run(m,inputs=None,params=None):
    inputs=inputs or {}; p=m.resolved_params(params or {}); m.validate(inputs,p); o=m.execute(inputs,p,CTX); return o,m.verify(inputs,p,o,CTX)
def pipeline():
    M,_=run(SimplexMeshND(),params={'vertices':'[[0,0],[1,0],[0,1],[0.3333333333333333,0.3333333333333333]]','elements':'[[0,1,3],[1,2,3],[2,0,3]]'}); mesh=M['mesh']
    sp,_=run(P1SimplexSpaceND(),{'mesh':mesh}); geo,_=run(CertifiedTriangleGeometry2D(),{'mesh':mesh}); diff,_=run(CertifiedDiffusion2D(),params={'tensor':'[[1,0],[0,1]]'})
    ia,_=run(IntervalGlobalAssembly2D(),{'mesh':mesh,'geometry_certificate':geo['geometry_certificate'],'diffusion_certificate':diff['diffusion_certificate']})
    asm,_=run(CertifiedPoissonAssembly(),{'mesh':mesh,'space':sp['space']},{'diffusion':'1.0','source_constant':1.0,'source_linear':'[0.5,-0.25]'})
    sol,_=run(LinearSolverND(),{'system':asm['system']})
    src,_=run(AffineSourceNorm2D(),{'problem':asm['problem']}); stab,_=run(ReferenceTriangleStability2D(),{'mesh':mesh,'diffusion_certificate':diff['diffusion_certificate'],'source_norm_certificate':src['source_norm_certificate']})
    ce,_=run(ComputedEnergyNorm2D(),{'interval_system':ia['interval_system'],'solution':sol['solution']}); err,recs=run(ExactSolutionFreeErrorBound2D(),{'stability_certificate':stab['stability_certificate'],'computed_energy_certificate':ce['computed_energy_certificate']})
    return mesh,sol,src,stab,ce,err,recs

def test_source_norm_positive_and_certified():
    *_,src,stab,ce,err,recs = pipeline()
    assert src['source_norm_certificate']['l2_norm_interval'][0] > 0

def test_exact_solution_free_error_bound_passes():
    mesh,sol,src,stab,ce,err,recs=pipeline(); c=err['solution_free_error_certificate']
    assert c['certified'] and not c['requires_exact_solution'] and c['energy_error_interval'][1] > 0
    assert recs[0].state.value=='pass'

def test_stability_uses_explicit_poincare_constant():
    mesh,sol,src,stab,ce,err,recs=pipeline(); cp=stab['stability_certificate']['poincare_upper']
    assert cp >= 1/math.pi and stab['stability_certificate']['continuum_solution_energy_upper']>0

def test_visualization_generates_real_png(tmp_path):
    mesh,sol,*_=pipeline(); out=tmp_path/'fem_solution.png'
    o,recs=run(FEMVisualization2D(),{'mesh':mesh,'solution':sol['solution']},{'output_path':str(out),'title':'v0.8 visualization test'})
    assert out.exists() and out.stat().st_size>1000 and o['visualization']['format']=='png'
    assert recs[0].state.value=='pass'
    # Verify PNG signature, not merely a file with .png extension.
    assert out.read_bytes()[:8] == b'\x89PNG\r\n\x1a\n'
