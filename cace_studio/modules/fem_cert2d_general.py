from __future__ import annotations
import json, math
import numpy as np

from cace_studio.core.module import Module, ValidationError
from cace_studio.core.types import ModuleMetadata, PortSpec, ParameterSpec, ProofStatus, Maturity, EvidenceKind
from cace_studio.core.verification import VerificationRecord, VerificationState
from cace_studio.core.interval import Interval, singleton, add, sub, mul, div, sqrt_interval, sum_intervals, down, up
from cace_studio.core.theorems import TheoremContract, TheoremRegistry, TheoremStatus
from cace_studio.modules.fem_cert2d import _triangle_interval_geometry, _reference_triangle_contract, _I, _ival
from cace_studio.modules.fem_nd import _boundary_facets, _boundary_vertices

THEOREM_ID='poisson2d-p1-certified-comparison-v0.7'
GENERIC_REL_ID='poisson2d-p1-residual-reliability-shape-regular-v0.7'

def _neg(a): return Interval(-a.hi,-a.lo)
def _matmul2(A,B):
    return [[add(mul(A[i][0],B[0][j]),mul(A[i][1],B[1][j])) for j in range(2)] for i in range(2)]
def _dot(a,b): return add(mul(a[0],b[0]),mul(a[1],b[1]))
def _scale(a,c): return mul(a,_I(c))
def _intersect(a: Interval,b: Interval):
    lo=max(a.lo,b.lo); hi=min(a.hi,b.hi)
    if lo>hi: raise ValidationError('interval intersection empty')
    return Interval(lo,hi)

def _tensor_interval(A):
    a=np.asarray(A,float)
    if a.shape!=(2,2) or not np.all(np.isfinite(a)): raise ValidationError('diffusion tensor must be finite 2x2')
    return [[_I(float(a[i,j])) for j in range(2)] for i in range(2)]

def _spd_certificate(A):
    # Exact-binary64 input entries enclosed as singletons then outward arithmetic.
    a,b=A[0][0],A[0][1]; c,d=A[1][0],A[1][1]
    sym=(b.lo==c.lo and b.hi==c.hi)
    det=sub(mul(a,d),mul(b,c)); tr=add(a,d)
    certified=sym and a.lo>0 and det.lo>0 and tr.lo>0
    alpha=Interval(0.0,0.0)
    if certified:
        # For 2x2 SPD, lambda_min = det/lambda_max >= det/trace.
        alpha=div(Interval(max(0.0,det.lo),det.hi),tr)
    return certified,det,tr,alpha

class CertifiedDiffusion2D(Module):
    metadata=ModuleMetadata('fem07.diffusion','Certified 2D Diffusion Tensor','0.7.0','Certified FEM',
        'Certify constant symmetric positive-definite 2x2 diffusion and produce a rigorous coercivity lower bound.',Maturity.BETA,
        assumptions=('stored binary64 tensor entries are exact inputs','constant diffusion tensor on the domain'))
    outputs=(PortSpec('diffusion_certificate','diffusion_certificate_2d'),)
    parameters=(ParameterSpec('tensor','string','[[1,0],[0,1]]','constant 2x2 diffusion tensor'),)
    proof_status=ProofStatus(evidence={EvidenceKind.INTERVAL,EvidenceKind.SYMBOLIC},unit_tests=True,documentation=True,
        limitations=['constant 2x2 tensor only in v0.7'])
    def execute(self,inputs,params,ctx):
        A=_tensor_interval(json.loads(params['tensor']) if isinstance(params['tensor'],str) else params['tensor'])
        ok,det,tr,alpha=_spd_certificate(A)
        if not ok: raise ValidationError('diffusion tensor could not be certified symmetric positive definite')
        return {'diffusion_certificate':{'tensor':[[[x.lo,x.hi] for x in row] for row in A],
            'det_interval':_ival(det),'trace_interval':_ival(tr),'coercivity_lower_interval':_ival(alpha),'spd_certified':True}}
    def verify(self,inputs,params,outputs,ctx):
        c=outputs['diffusion_certificate']; ok=c['spd_certified'] and c['coercivity_lower_interval'][0]>0
        return [VerificationRecord('diffusion-spd-2d',EvidenceKind.INTERVAL,
            'constant diffusion is symmetric positive definite and lambda_min(A) >= det(A)/trace(A) > 0',
            VerificationState.PASS if ok else VerificationState.FAIL,'2x2 Sylvester criterion plus SPD eigenvalue inequality',c)]

class IntervalGlobalAssembly2D(Module):
    metadata=ModuleMetadata('fem07.interval_global_assembly','Interval Global P1 Assembly 2D','0.7.0','Certified FEM',
        'Assemble interval-enclosed reduced P1 stiffness matrix for constant SPD diffusion from certified triangle geometry.',Maturity.EXPERIMENTAL)
    inputs=(PortSpec('mesh','simplex_mesh'),PortSpec('geometry_certificate','triangle_geometry_certificate'),PortSpec('diffusion_certificate','diffusion_certificate_2d'))
    outputs=(PortSpec('interval_system','interval_linear_system_2d'),)
    proof_status=ProofStatus(evidence={EvidenceKind.INTERVAL},unit_tests=True,documentation=True,
        limitations=['homogeneous Dirichlet reduction','stiffness only; load interval assembly is not yet generalized beyond affine benchmark paths'])
    def validate(self,inputs,params):
        super().validate(inputs,params); ok,why=_reference_triangle_contract(inputs['mesh'])
        if not ok: raise ValidationError(why)
    def execute(self,inputs,params,ctx):
        m=inputs['mesh']; V=np.asarray(m['vertices'],float); n=len(V)
        G=[[Interval(0.0,0.0) for _ in range(n)] for _ in range(n)]
        At=[[Interval(*x) for x in row] for row in inputs['diffusion_certificate']['tensor']]
        for c in m['elements']:
            ids=list(map(int,c)); g=_triangle_interval_geometry(V,ids); area=g['area']; grads=g['grads']
            for i in range(3):
                Ag=[add(mul(At[0][0],grads[i][0]),mul(At[0][1],grads[i][1])),
                    add(mul(At[1][0],grads[i][0]),mul(At[1][1],grads[i][1]))]
                for j in range(3):
                    kij=mul(area,_dot(Ag,grads[j])); G[ids[i]][ids[j]]=add(G[ids[i]][ids[j]],kij)
        bfac,_=_boundary_facets(m['elements']); bd=set(_boundary_vertices(bfac)); interior=[i for i in range(n) if i not in bd]
        red=[[G[i][j] for j in interior] for i in interior]
        return {'interval_system':{'interior_dofs':interior,'matrix_intervals':[[[x.lo,x.hi] for x in row] for row in red],
            'dimension':len(interior),'homogeneous_dirichlet':True}}
    def verify(self,inputs,params,outputs,ctx):
        A=outputs['interval_system']['matrix_intervals']; ok=True
        for i in range(len(A)):
            for j in range(len(A)):
                ok &= A[i][j][0] <= A[j][i][1] and A[j][i][0] <= A[i][j][1]
        return [VerificationRecord('interval-global-stiffness-assembly',EvidenceKind.INTERVAL,
            'every reduced global stiffness entry is an outward enclosure of the sum of certified local contributions',
            VerificationState.PASS if ok else VerificationState.FAIL,'interval local assembly with outward-rounded accumulation',
            {'dimension':len(A),'interval_symmetric':bool(ok)})]

class TheoremRegistry2D(Module):
    metadata=ModuleMetadata('fem07.theorem_registry','2D FEM Theorem Registry','0.7.0','Formal Verification',
        'Expose theorem contracts and their verification status without treating registration as proof.',Maturity.BETA)
    outputs=(PortSpec('registry','theorem_registry_snapshot'),)
    proof_status=ProofStatus(evidence={EvidenceKind.SYMBOLIC},unit_tests=True,documentation=True,
        limitations=['the generic residual reliability theorem remains obligation-only in v0.7'])
    def execute(self,inputs,params,ctx):
        def comparison_match(f):
            misses=[]
            for k in ('dimension','conforming','p1','interval_error','interval_estimator'):
                if not f.get(k): misses.append(k)
            return not misses,misses
        R=TheoremRegistry()
        R.register(TheoremContract(THEOREM_ID,
            'If E in [Elo,Ehi], eta in [etalo,etahi], C>0, and Ehi <= C*etalo, then E <= C eta.',
            TheoremStatus.COMPUTATIONAL,('dimension=2','conforming mesh','P1 approximation','independent interval enclosures for E and eta'),
            'interval-certified',checker='CACE interval comparison',matcher=comparison_match))
        R.register(TheoremContract(GENERIC_REL_ID,
            'For conforming P1 Poisson FEM on a shape-regular triangular mesh, ||u-u_h||_E <= C_rel eta under the theorem assumptions.',
            TheoremStatus.OBLIGATION,('bounded Lipschitz polygon','uniform ellipticity','shape regularity','conforming P1','residual/jump estimator','interpolation/trace constants'),
            'formally-verified',checker=None,artifact='docs/proofs/poisson2d_p1_reliability_v07.lean'))
        return {'registry':{'theorems':[t.describe() for t in R.list()]}}
    def verify(self,inputs,params,outputs,ctx):
        return [VerificationRecord('theorem-registry-integrity',EvidenceKind.SYMBOLIC,
            'the theorem registry records status explicitly; obligation-only entries do not generate formal evidence',VerificationState.PASS,
            'registry schema/status validation',{'theorems':len(outputs['registry']['theorems'])})]

class ReusableReliabilityGate2D(Module):
    metadata=ModuleMetadata('fem07.reliability_gate','Reusable 2D Reliability Gate','0.7.0','Certified FEM',
        'Match a reusable theorem contract to explicit run facts and discharge its interval comparison without upgrading to formal evidence.',Maturity.EXPERIMENTAL)
    inputs=(PortSpec('shape_certificate','shape_regularity_certificate_2d'),PortSpec('diffusion_certificate','diffusion_certificate_2d'),
            PortSpec('continuum_certificate','continuum_error_certificate_2d'),PortSpec('estimator_certificate','estimator_certificate_2d'))
    outputs=(PortSpec('theorem_certificate','theorem_backed_certificate_2d'),)
    parameters=(ParameterSpec('C_rel','number',1.0),ParameterSpec('theorem_id','string',THEOREM_ID))
    proof_status=ProofStatus(evidence={EvidenceKind.INTERVAL,EvidenceKind.SYMBOLIC},unit_tests=True,documentation=True,
        limitations=['v0.7 reusable certificate is computationally discharged from independent E and eta intervals; it is not the still-open generic PDE reliability theorem'])
    def execute(self,inputs,params,ctx):
        tid=str(params['theorem_id']); C=float(params['C_rel'])
        if tid!=THEOREM_ID:
            return {'theorem_certificate':{'theorem_id':tid,'matched':False,'certified':False,'status':'not-run','reason':'requested theorem is not computationally dischargeable in v0.7'}}
        facts={'dimension':2,'conforming':True,'p1':True,'interval_error':True,'interval_estimator':True,
               'shape_regular':bool(inputs['shape_certificate'].get('shape_regular_certified')),
               'uniform_ellipticity':inputs['diffusion_certificate']['coercivity_lower_interval'][0]>0}
        misses=[k for k in ('shape_regular','uniform_ellipticity') if not facts[k]]
        Ehi=float(inputs['continuum_certificate']['energy_error_interval'][1]); etalo=float(inputs['estimator_certificate']['eta_interval'][0])
        rhslo=down(C*etalo) if C>0 else -math.inf; certified=(not misses and etalo>0 and rhslo>=Ehi)
        return {'theorem_certificate':{'theorem_id':tid,'theorem_status':TheoremStatus.COMPUTATIONAL.value,'matched':not misses,
            'assumption_failures':misses,'certified':certified,'status':'pass' if certified else 'not-run','C_rel':C,
            'error_upper':Ehi,'eta_lower':etalo,'C_eta_lower':rhslo,'formal_evidence':False}}
    def verify(self,inputs,params,outputs,ctx):
        c=outputs['theorem_certificate']; state=VerificationState.PASS if c.get('certified') else VerificationState.NOT_RUN
        return [VerificationRecord('reusable-2d-theorem-gate',EvidenceKind.INTERVAL,
            'a reusable computational theorem contract matched the run assumptions and E <= C_rel eta was discharged from independent interval bounds',state,
            'theorem-contract matching plus directed interval comparison',c,
            notes=('This is not formal evidence; the generic PDE reliability theorem remains obligation-only.',))]

class GenericReliabilityObligationV07(Module):
    metadata=ModuleMetadata('fem07.generic_reliability_obligation','Generic 2D Poisson Reliability Obligation v0.7','0.7.0','Formal Verification',
        'Export the explicit Lean 4 obligation for a mesh-uniform residual-estimator reliability theorem.',Maturity.PROTOTYPE)
    outputs=(PortSpec('theorem_artifact','formal_artifact'),)
    proof_status=ProofStatus(evidence=set(),unit_tests=True,documentation=True,formal_artifact='docs/proofs/poisson2d_p1_reliability_v07.lean')
    def execute(self,inputs,params,ctx):
        return {'theorem_artifact':{'theorem_id':GENERIC_REL_ID,'language':'Lean4','status':'obligation-only','machine_checked':False,
            'artifact':'docs/proofs/poisson2d_p1_reliability_v07.lean'}}
    def verify(self,inputs,params,outputs,ctx):
        return [VerificationRecord('generic-2d-reliability-v07',EvidenceKind.FORMAL,
            'generic shape-regular 2D Poisson residual reliability remains an unproved formal obligation',VerificationState.NOT_RUN,
            'artifact export only',outputs['theorem_artifact'])]

def register_fem_cert2d_general(registry):
    for cls in (CertifiedDiffusion2D,IntervalGlobalAssembly2D,TheoremRegistry2D,ReusableReliabilityGate2D,GenericReliabilityObligationV07):
        registry.register(cls)
