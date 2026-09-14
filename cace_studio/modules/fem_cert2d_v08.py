from __future__ import annotations
import math, os
import numpy as np

from cace_studio.core.module import Module, ValidationError
from cace_studio.core.types import ModuleMetadata, PortSpec, ParameterSpec, ProofStatus, Maturity, EvidenceKind
from cace_studio.core.verification import VerificationRecord, VerificationState
from cace_studio.core.interval import Interval, add, mul, div, sqrt_interval, down, up
from cace_studio.modules.fem_cert2d import _reference_triangle_contract

STABILITY_ID='poisson2d-reference-triangle-energy-stability-v0.8'

def I(x): return Interval(float(x),float(x))
def il(a): return [a.lo,a.hi]

def affine_source_l2(c,lx,ly):
    # Exact reference-triangle moments: int 1=1/2, x=y=1/6, x^2=y^2=1/12, xy=1/24.
    c,lx,ly=I(c),I(lx),I(ly)
    s=mul(mul(c,c),I(0.5))
    s=add(s,mul(mul(I(2.0),mul(c,lx)),I(1.0/6.0)))
    s=add(s,mul(mul(I(2.0),mul(c,ly)),I(1.0/6.0)))
    s=add(s,mul(mul(lx,lx),I(1.0/12.0)))
    s=add(s,mul(mul(ly,ly),I(1.0/12.0)))
    s=add(s,mul(mul(I(2.0),mul(lx,ly)),I(1.0/24.0)))
    return sqrt_interval(Interval(max(0.0,s.lo),max(0.0,s.hi)))

def quadratic_interval(A, u):
    q=Interval(0.0,0.0)
    for i,ui in enumerate(u):
        for j,uj in enumerate(u):
            a=Interval(*A[i][j])
            q=add(q,mul(mul(I(ui),a),I(uj)))
    return Interval(max(0.0,q.lo),max(0.0,q.hi))

class AffineSourceNorm2D(Module):
    metadata=ModuleMetadata('fem08.source_norm','Certified Affine Source Norm','0.8.0','Certified FEM',
        'Certify the L2 norm of affine forcing f=c+lx*x+ly*y on the reference triangle from exact monomial moments.',Maturity.BETA)
    inputs=(PortSpec('problem','certified_poisson_problem'),)
    outputs=(PortSpec('source_norm_certificate','source_norm_certificate_2d'),)
    proof_status=ProofStatus(evidence={EvidenceKind.INTERVAL,EvidenceKind.SYMBOLIC},unit_tests=True,documentation=True)
    def validate(self,inputs,params):
        super().validate(inputs,params)
        p=inputs['problem']; lin=p.get('source_linear',[])
        if p.get('dimension')!=2 or len(lin)!=2: raise ValidationError('v0.8 source norm requires a 2D affine source')
    def execute(self,inputs,params,ctx):
        p=inputs['problem']; c=float(p.get('source_constant',0.0)); lx,ly=map(float,p['source_linear']); n=affine_source_l2(c,lx,ly)
        return {'source_norm_certificate':{'domain':'reference_triangle','source':[c,lx,ly],'l2_norm_interval':il(n),'certified':True}}
    def verify(self,inputs,params,outputs,ctx):
        c=outputs['source_norm_certificate']; lo,hi=c['l2_norm_interval']; ok=0<=lo<=hi
        return [VerificationRecord('affine-source-l2-reference-triangle',EvidenceKind.INTERVAL,
            'the L2 norm of affine f is enclosed using exact reference-triangle monomial moments and outward rounding',
            VerificationState.PASS if ok else VerificationState.FAIL,'exact moments plus interval arithmetic',c)]

class ReferenceTriangleStability2D(Module):
    metadata=ModuleMetadata('fem08.stability_bound','Exact-Solution-Free Continuum Stability Bound','0.8.0','Certified FEM',
        'Bound the continuum solution energy without knowing the exact solution, using the reference-triangle slice Poincare constant, source norm, and diffusion coercivity.',Maturity.EXPERIMENTAL,
        assumptions=('domain is the reference triangle','homogeneous Dirichlet boundary conditions','constant SPD diffusion'))
    inputs=(PortSpec('mesh','simplex_mesh'),PortSpec('diffusion_certificate','diffusion_certificate_2d'),PortSpec('source_norm_certificate','source_norm_certificate_2d'))
    outputs=(PortSpec('stability_certificate','continuum_stability_certificate_2d'),)
    proof_status=ProofStatus(evidence={EvidenceKind.INTERVAL,EvidenceKind.SYMBOLIC},unit_tests=True,documentation=True,
        limitations=['reference-triangle theorem only in v0.8; this is a stability upper bound, not a residual-estimator reliability constant'])
    def validate(self,inputs,params):
        super().validate(inputs,params); ok,why=_reference_triangle_contract(inputs['mesh'])
        if not ok: raise ValidationError(why)
    def execute(self,inputs,params,ctx):
        alpha=float(inputs['diffusion_certificate']['coercivity_lower_interval'][0]); fhi=float(inputs['source_norm_certificate']['l2_norm_interval'][1])
        if alpha<=0: return {'stability_certificate':{'certified':False,'status':'not-run','reason':'nonpositive certified coercivity'}}
        # Horizontal-slice Dirichlet Poincare on T={(x,y):0<y<1,0<x<1-y}: Cp <= 1/pi.
        pi_lo=down(math.pi); cp_hi=up(1.0/pi_lo)
        bound=up(cp_hi*fhi/math.sqrt(alpha))
        return {'stability_certificate':{'theorem_id':STABILITY_ID,'certified':True,'domain':'reference_triangle','poincare_upper':cp_hi,
            'diffusion_coercivity_lower':alpha,'source_l2_upper':fhi,'continuum_solution_energy_upper':bound,
            'derivation':'||u||_A^2=(f,u)<=||f|| Cp ||grad u||<=Cp||f||/sqrt(alpha) ||u||_A'}}
    def verify(self,inputs,params,outputs,ctx):
        c=outputs['stability_certificate']; state=VerificationState.PASS if c.get('certified') else VerificationState.NOT_RUN
        return [VerificationRecord('reference-triangle-continuum-stability',EvidenceKind.INTERVAL,
            'continuum energy norm is bounded without an exact solution by slice Poincare plus certified ellipticity and source norm',state,
            'weak-form energy identity and 1D Dirichlet Poincare on horizontal triangle slices',c,
            notes=('The mathematical theorem is encoded as a reviewed symbolic contract, not a machine-checked Lean proof.',))]

class ComputedEnergyNorm2D(Module):
    metadata=ModuleMetadata('fem08.computed_energy','Certified Computed FEM Energy Norm','0.8.0','Certified FEM',
        'Enclose sqrt(u_h^T A_h u_h) from the interval global stiffness matrix and computed interior coefficients.',Maturity.BETA)
    inputs=(PortSpec('interval_system','interval_linear_system_2d'),PortSpec('solution','fem_solution_nd'))
    outputs=(PortSpec('computed_energy_certificate','computed_energy_certificate_2d'),)
    proof_status=ProofStatus(evidence={EvidenceKind.INTERVAL},unit_tests=True,documentation=True)
    def execute(self,inputs,params,ctx):
        A=inputs['interval_system']['matrix_intervals']; u=list(map(float,inputs['solution']['interior']))
        if len(A)!=len(u): raise ValidationError('interval system and solution dimension mismatch')
        q=quadratic_interval(A,u); e=sqrt_interval(q)
        return {'computed_energy_certificate':{'energy_squared_interval':il(q),'energy_interval':il(e),'certified':True}}
    def verify(self,inputs,params,outputs,ctx):
        c=outputs['computed_energy_certificate']; lo,hi=c['energy_interval']; ok=0<=lo<=hi
        return [VerificationRecord('computed-p1-energy-norm',EvidenceKind.INTERVAL,'computed P1 energy norm is enclosed from interval global stiffness data',VerificationState.PASS if ok else VerificationState.FAIL,'interval quadratic form',c)]

class ExactSolutionFreeErrorBound2D(Module):
    metadata=ModuleMetadata('fem08.solution_free_error','Exact-Solution-Free 2D Error Bound','0.8.0','Certified FEM',
        'Certify a conservative continuum energy-error upper bound without a manufactured exact solution using ||u-u_h||_A <= ||u||_A + ||u_h||_A.',Maturity.EXPERIMENTAL)
    inputs=(PortSpec('stability_certificate','continuum_stability_certificate_2d'),PortSpec('computed_energy_certificate','computed_energy_certificate_2d'))
    outputs=(PortSpec('solution_free_error_certificate','solution_free_error_certificate_2d'),)
    proof_status=ProofStatus(evidence={EvidenceKind.INTERVAL,EvidenceKind.SYMBOLIC},unit_tests=True,documentation=True,
        limitations=['conservative triangle-inequality bound; v0.8 does not yet supply the sharper general residual-reliability constant'])
    def execute(self,inputs,params,ctx):
        s=inputs['stability_certificate']; h=inputs['computed_energy_certificate']
        if not s.get('certified') or not h.get('certified'): return {'solution_free_error_certificate':{'certified':False,'status':'not-run'}}
        ub=up(float(s['continuum_solution_energy_upper'])+float(h['energy_interval'][1]))
        return {'solution_free_error_certificate':{'certified':True,'theorem_id':'energy-triangle-bound-v0.8','energy_error_interval':[0.0,ub],
            'continuum_solution_energy_upper':s['continuum_solution_energy_upper'],'computed_energy_upper':h['energy_interval'][1],
            'requires_exact_solution':False,'formal_evidence':False}}
    def verify(self,inputs,params,outputs,ctx):
        c=outputs['solution_free_error_certificate']; state=VerificationState.PASS if c.get('certified') else VerificationState.NOT_RUN
        return [VerificationRecord('exact-solution-free-continuum-error',EvidenceKind.INTERVAL,
            'a conservative continuum energy-error upper bound is certified without access to an exact manufactured solution',state,
            'triangle inequality composed with certified continuum stability and computed FEM energy norm',c)]

class FEMVisualization2D(Module):
    metadata=ModuleMetadata('viz08.fem_solution','FEM Solution Visualization 2D','0.8.0','Visualization',
        'Render a reproducible PNG of triangular mesh and computed nodal solution values for visualization smoke testing.',Maturity.BETA)
    inputs=(PortSpec('mesh','simplex_mesh'),PortSpec('solution','fem_solution_nd'))
    outputs=(PortSpec('visualization','visualization_artifact'),)
    parameters=(ParameterSpec('output_path','string','examples/v08_fem_solution.png'),ParameterSpec('title','string','CACE v0.8 FEM solution'))
    proof_status=ProofStatus(evidence={EvidenceKind.EXPERIMENTAL},unit_tests=True,documentation=True,
        limitations=['visualization is an inspection artifact and contributes no mathematical proof evidence'])
    def execute(self,inputs,params,ctx):
        try:
            import matplotlib; matplotlib.use('Agg',force=True)
            import matplotlib.pyplot as plt
            import matplotlib.tri as mtri
        except Exception as e: raise ValidationError(f'matplotlib unavailable: {e}')
        V=np.asarray(inputs['mesh']['vertices'],float); E=np.asarray(inputs['mesh']['elements'],int); u=np.asarray(inputs['solution']['values'],float)
        if inputs['mesh'].get('dimension')!=2: raise ValidationError('v0.8 FEM visualization requires a 2D mesh')
        path=str(params['output_path']); os.makedirs(os.path.dirname(path) or '.',exist_ok=True)
        tri=mtri.Triangulation(V[:,0],V[:,1],E)
        fig,ax=plt.subplots(figsize=(6,5)); tpc=ax.tripcolor(tri,u,shading='gouraud'); ax.triplot(tri,linewidth=0.8); fig.colorbar(tpc,ax=ax,label='u_h')
        ax.set_title(str(params['title'])); ax.set_xlabel('x'); ax.set_ylabel('y'); ax.set_aspect('equal'); fig.tight_layout(); fig.savefig(path,dpi=140); plt.close(fig)
        return {'visualization':{'path':path,'format':'png','vertices':len(V),'elements':len(E),'value_min':float(u.min()),'value_max':float(u.max()),'bytes':os.path.getsize(path)}}
    def verify(self,inputs,params,outputs,ctx):
        a=outputs['visualization']; ok=os.path.exists(a['path']) and a['bytes']>1000
        return [VerificationRecord('visualization-png-smoke-test',EvidenceKind.EXPERIMENTAL,'PNG visualization was generated from actual experiment mesh/solution data and is nonempty',VerificationState.PASS if ok else VerificationState.FAIL,'headless Matplotlib render plus file existence/size check',a)]

def register_fem_v08(registry):
    for cls in (AffineSourceNorm2D,ReferenceTriangleStability2D,ComputedEnergyNorm2D,ExactSolutionFreeErrorBound2D,FEMVisualization2D): registry.register(cls)
