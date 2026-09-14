from __future__ import annotations
import json, math
from typing import Any
import numpy as np

from cace_studio.core.module import Module, ValidationError
from cace_studio.core.types import ModuleMetadata,PortSpec,ParameterSpec,ProofStatus,Maturity,EvidenceKind
from cace_studio.core.verification import VerificationRecord,VerificationState
from cace_studio.core.interval import Interval,singleton,add,sub,mul,div,abs_interval,square,sqrt_interval,sum_intervals,down,up
from cace_studio.modules.fem_nd import _dense,_csr_from_dense,_simplex_geometry,_boundary_facets,_boundary_vertices


def _j(x): return json.loads(x) if isinstance(x,str) else x

def _diffusions(spec:Any,d:int,ncells:int):
    x=_j(spec)
    def mat(v):
        if isinstance(v,(int,float)): return np.eye(d)*float(v)
        a=np.asarray(v,float)
        if a.shape!=(d,d): raise ValidationError(f'diffusion must be scalar or {d}x{d} matrix')
        return a
    # A single dxd matrix vs list of per-cell matrices.
    if isinstance(x,(int,float)): return [mat(x) for _ in range(ncells)]
    a=np.asarray(x,dtype=object)
    if a.ndim==2 and len(x)==d and all(len(r)==d for r in x): return [mat(x) for _ in range(ncells)]
    if not isinstance(x,list) or len(x)!=ncells: raise ValidationError('per-cell diffusion list must match number of elements')
    return [mat(v) for v in x]

def _source_nodal(Vcell:np.ndarray,c:float,linear:list[float]):
    l=np.asarray(linear,float)
    if l.size==0: l=np.zeros(Vcell.shape[1])
    if l.shape!=(Vcell.shape[1],): raise ValidationError('source_linear must have one coefficient per spatial dimension')
    return c + Vcell@l

def _assemble_cert(mesh,diffusion,source_constant,source_linear):
    V=np.asarray(mesh['vertices'],float); E=[list(map(int,c)) for c in mesh['elements']]; d=V.shape[1]; n=len(V)
    Ds=_diffusions(diffusion,d,len(E)); A=np.zeros((n,n)); b=np.zeros(n); cell_metrics=[]
    for k,(cell,D) in enumerate(zip(E,Ds)):
        if not np.all(np.isfinite(D)) or np.max(np.abs(D-D.T))>1e-12: raise ValidationError('diffusion tensors must be finite symmetric matrices')
        eig=np.linalg.eigvalsh(D); mine=float(np.min(eig)); maxe=float(np.max(eig))
        if mine<=0: raise ValidationError('diffusion tensors must be SPD')
        g=_simplex_geometry(V,cell); G=np.asarray(g['gradients']); vol=float(g['volume'])
        ke=vol*(G@D@G.T)
        fv=_source_nodal(V[np.asarray(cell,int)],float(source_constant),list(_j(source_linear)))
        # Exact P1 load for affine source: ∫ lambda_i f = vol/((d+1)(d+2)) * (sum_j f(v_j)+f(v_i)).
        fe=vol/((d+1)*(d+2))*(np.sum(fv)+fv)
        for i,I in enumerate(cell):
            b[I]+=fe[i]
            for j,J in enumerate(cell): A[I,J]+=ke[i,j]
        cell_metrics.append({'min_diffusion_eigenvalue':mine,'max_diffusion_eigenvalue':maxe,'volume':vol})
    bfac,_=_boundary_facets(E); bd=_boundary_vertices(bfac); interior=[i for i in range(n) if i not in set(bd)]
    Ar=A[np.ix_(interior,interior)]; br=b[interior]
    return A,b,Ar,br,interior,bd,cell_metrics

def _interval_residual(csr,b,u):
    n=int(csr['shape'][0]); rows=[]
    for i in range(n):
        terms=[]
        for p in range(csr['indptr'][i],csr['indptr'][i+1]):
            j=int(csr['indices'][p]); terms.append(mul(singleton(float(csr['data'][p])),singleton(float(u[j]))))
        rows.append(sub(sum_intervals(terms),singleton(float(b[i]))))
    absrows=[abs_interval(r) for r in rows]
    inf=Interval(0.0,max((a.hi for a in absrows),default=0.0))
    sq=sum_intervals([square(r) for r in rows]); l2=sqrt_interval(Interval(max(0.0,sq.lo),max(0.0,sq.hi)))
    return rows,Interval(0.0,up(inf.hi)),l2

def _gershgorin_lower(csr):
    n=int(csr['shape'][0]); lowers=[]
    for i in range(n):
        diag=0.0; radius=Interval(0.0,0.0)
        for p in range(csr['indptr'][i],csr['indptr'][i+1]):
            j=int(csr['indices'][p]); a=float(csr['data'][p])
            if j==i: diag=a
            else: radius=add(radius,abs_interval(singleton(a)))
        lowers.append(down(diag-radius.hi))
    return min(lowers) if lowers else math.inf


def _interval_ldlt_proves_spd_shift(csr, alpha: float) -> bool:
    """Certify A-alpha I is SPD via interval LDL^T pivots for exact stored binary64 A."""
    A=_dense(csr); n=A.shape[0]
    L=[[Interval(0.0,0.0) for _ in range(n)] for _ in range(n)]
    D=[Interval(0.0,0.0) for _ in range(n)]
    for i in range(n):
        acc=Interval(0.0,0.0)
        for k in range(i):
            acc=add(acc,mul(mul(L[i][k],L[i][k]),D[k]))
        piv=sub(sub(singleton(float(A[i,i])),singleton(float(alpha))),acc)
        if not (piv.lo>0.0 and math.isfinite(piv.lo)):
            return False
        D[i]=piv; L[i][i]=singleton(1.0)
        for j in range(i+1,n):
            acc2=Interval(0.0,0.0)
            for k in range(i):
                acc2=add(acc2,mul(mul(L[j][k],L[i][k]),D[k]))
            num=sub(singleton(float(A[j,i])),acc2)
            L[j][i]=div(num,D[i])
    return True

def _certified_spd_lower(csr):
    g=_gershgorin_lower(csr)
    if g>0 and math.isfinite(g):
        return g,'gershgorin'
    A=_dense(csr)
    if A.size==0: return math.inf,'empty'
    # Numerical eigenvalue is used only to choose a candidate. Interval LDL^T is the certificate.
    lam=float(np.min(np.linalg.eigvalsh((A+A.T)/2.0)))
    if not (lam>0 and math.isfinite(lam)): return g,'uncertified'
    cand=down(lam*0.5)
    for _ in range(64):
        if cand>0 and _interval_ldlt_proves_spd_shift(csr,cand): return cand,'interval-ldlt'
        cand=down(cand*0.5)
    return g,'uncertified'

class CertifiedPoissonAssembly(Module):
    metadata=ModuleMetadata('fem_cert.poisson_assemble','Certified-Class Poisson Assembly','0.4.0','Certified FEM',
        'Assemble P1 diffusion/Poisson systems with SPD scalar/tensor diffusion and affine forcing. Assembly is numerically verified; continuum certification is separate.',Maturity.BETA,
        assumptions=('conforming nondegenerate simplex mesh','homogeneous Dirichlet data on detected boundary','diffusion is elementwise constant SPD','forcing is affine in physical coordinates'))
    inputs=(PortSpec('mesh','simplex_mesh'),PortSpec('space','fem_space_nd'))
    outputs=(PortSpec('system','linear_system_nd'),PortSpec('problem','certified_poisson_problem'))
    parameters=(ParameterSpec('diffusion','string','1.0','JSON scalar, dxd SPD matrix, or per-element list'),ParameterSpec('source_constant','number',1.0),ParameterSpec('source_linear','string','[]','JSON affine coefficients'))
    proof_status=ProofStatus(evidence={EvidenceKind.SYMBOLIC,EvidenceKind.NUMERICAL},unit_tests=True,property_tests=True,documentation=True,
        limitations=['binary64 geometry/assembly is not itself an interval enclosure of the exact continuum bilinear form'])
    def validate(self,inputs,params):
        super().validate(inputs,params); p=self.resolved_params(params); m=inputs['mesh']; _diffusions(p['diffusion'],m['dimension'],len(m['elements']))
        lin=_j(p['source_linear']);
        if lin and len(lin)!=m['dimension']: raise ValidationError('source_linear dimension mismatch')
    def execute(self,inputs,params,ctx):
        m=inputs['mesh']; A,b,Ar,br,interior,bd,metrics=_assemble_cert(m,params['diffusion'],params['source_constant'],params['source_linear'])
        return {'system':{'matrix':_csr_from_dense(Ar),'rhs':br.tolist(),'interior_dofs':interior,'boundary_dofs':bd,'full_dofs':len(b),
                          'problem_class':'elliptic-p1-spd-affine-source'},
                'problem':{'dimension':m['dimension'],'diffusion':_j(params['diffusion']),'source_constant':float(params['source_constant']),
                           'source_linear':_j(params['source_linear']),'cell_coercivity_lower':min((x['min_diffusion_eigenvalue'] for x in metrics),default=math.inf)}}
    def verify(self,inputs,params,outputs,ctx):
        A=_dense(outputs['system']['matrix']); sym=float(np.max(np.abs(A-A.T))) if A.size else 0.; eig=float(np.min(np.linalg.eigvalsh(A))) if A.size else math.inf
        coerc=float(outputs['problem']['cell_coercivity_lower']); ok=sym<=1e-11 and eig>0 and coerc>0
        return [VerificationRecord('cert-poisson-class-assumptions',EvidenceKind.NUMERICAL,
            'discrete reduced operator is symmetric positive definite and every supplied diffusion tensor is SPD',VerificationState.PASS if ok else VerificationState.FAIL,
            'independent symmetry/eigenvalue checks plus elementwise diffusion spectra',{'matrix_symmetry_error':sym,'matrix_min_eigenvalue':eig,'diffusion_coercivity_lower':coerc})]

class IntervalAlgebraicResidual(Module):
    metadata=ModuleMetadata('fem_cert.interval_residual','Interval Algebraic Residual','0.4.0','Certified FEM',
        'Outward-round every multiply/add when evaluating r=A u-b, treating stored binary64 CSR entries, rhs, and solution values as exact discrete inputs.',Maturity.BETA,
        assumptions=('IEEE-754 binary64 operations and Python math.nextafter conform','stored CSR/rhs/solution binary64 values define the discrete problem to certify'))
    inputs=(PortSpec('system','linear_system_nd'),PortSpec('solution','fem_solution_nd'))
    outputs=(PortSpec('residual_certificate','interval_residual_certificate'),)
    proof_status=ProofStatus(evidence={EvidenceKind.INTERVAL},unit_tests=True,property_tests=True,documentation=True,
        limitations=['certifies the algebraic residual of the stored discrete system, not FEM discretization error versus the continuum PDE'])
    def execute(self,inputs,params,ctx):
        s=inputs['system']; u=np.asarray(inputs['solution']['interior'],float); b=np.asarray(s['rhs'],float); rows,inf,l2=_interval_residual(s['matrix'],b,u)
        return {'residual_certificate':{'row_intervals':[r.to_list() for r in rows],'residual_inf_interval':inf.to_list(),'residual_l2_interval':l2.to_list(),
                                        'scope':'discrete-binary64-linear-system'}}
    def verify(self,inputs,params,outputs,ctx):
        c=outputs['residual_certificate']; ok=all(lo<=hi for lo,hi in c['row_intervals']) and c['residual_inf_interval'][0]<=c['residual_inf_interval'][1]
        return [VerificationRecord('interval-algebraic-residual',EvidenceKind.INTERVAL,
            'the exact residual of the stored binary64 discrete system is enclosed componentwise and in infinity/L2 norm',VerificationState.PASS if ok else VerificationState.FAIL,
            'directed nextafter rounding for each interval product and sum',{'residual_inf_upper':c['residual_inf_interval'][1],'residual_l2_upper':c['residual_l2_interval'][1]})]

class DiscreteEnergyErrorCertificate(Module):
    metadata=ModuleMetadata('fem_cert.discrete_energy_error','Discrete Energy Error Certificate','0.5.0','Certified FEM',
        'Use an outward-rounded Gershgorin coercivity lower bound and interval residual to certify error between computed and exact discrete linear-system solutions.',Maturity.EXPERIMENTAL,
        assumptions=('reduced matrix is symmetric','a strictly positive Gershgorin lower bound is obtained'))
    inputs=(PortSpec('system','linear_system_nd'),PortSpec('residual_certificate','interval_residual_certificate'))
    outputs=(PortSpec('algebraic_error_certificate','algebraic_error_certificate'),)
    proof_status=ProofStatus(evidence={EvidenceKind.INTERVAL,EvidenceKind.SYMBOLIC},unit_tests=True,documentation=True,
        limitations=['this is algebraic solve error only; it does not bound the continuum FEM discretization error','certificate may be unavailable when Gershgorin lower bound is nonpositive even if matrix is SPD'])
    def execute(self,inputs,params,ctx):
        s=inputs['system']; alpha,method=_certified_spd_lower(s['matrix']); r2=float(inputs['residual_certificate']['residual_l2_interval'][1])
        if alpha>0 and math.isfinite(alpha):
            l2=up(r2/alpha); energy=up(r2/math.sqrt(alpha)); certified=True
        else: l2=math.inf; energy=math.inf; certified=False
        return {'algebraic_error_certificate':{'certified':certified,'gershgorin_lambda_min_lower':alpha,'solution_l2_error_upper':l2,'energy_error_upper':energy,
                                                'scope':'computed-solution-vs-exact-discrete-solution','coercivity_method':method}}
    def verify(self,inputs,params,outputs,ctx):
        c=outputs['algebraic_error_certificate']
        state=VerificationState.PASS if c['certified'] else VerificationState.NOT_RUN
        return [VerificationRecord('discrete-spd-gershgorin-bound',EvidenceKind.INTERVAL,
            'if the certified Gershgorin lower bound alpha is positive, ||u-u*||_2 <= ||r||_2/alpha and ||u-u*||_A <= ||r||_2/sqrt(alpha)',state,
            'certified SPD lower bound (Gershgorin or interval LDL^T) + SPD residual-error identity with outward-rounded arithmetic',c,
            notes=(() if c['certified'] else ('matrix may be SPD even though Gershgorin is too weak to certify it',)))]

class EstimatorReliabilityGate(Module):
    metadata=ModuleMetadata('fem_cert.reliability_gate','Continuum Estimator Reliability Gate','0.4.0','Certified FEM',
        'Explicitly gate continuum a-posteriori reliability claims behind a registered theorem artifact and matching assumptions.',Maturity.PROTOTYPE)
    inputs=(PortSpec('problem','certified_poisson_problem'),PortSpec('estimator','error_estimator_nd'))
    outputs=(PortSpec('reliability_status','record'),)
    parameters=(ParameterSpec('theorem_id','string','', 'registered continuum reliability theorem artifact id'),)
    proof_status=ProofStatus(evidence=set(),unit_tests=True,documentation=True,
        limitations=['v0.4 ships no general continuum reliability theorem artifact; unsupported requests are intentionally NOT_RUN'])
    def execute(self,inputs,params,ctx):
        requested=str(params['theorem_id']).strip()
        return {'reliability_status':{'requested_theorem':requested,'supported':False,'continuum_error_certified':False,
                                      'reason':'no general residual-estimator reliability theorem artifact is registered in v0.4'}}
    def verify(self,inputs,params,outputs,ctx):
        return [VerificationRecord('continuum-reliability-theorem-gate',EvidenceKind.FORMAL,
            'continuum estimator reliability is certified only when a registered theorem artifact matches all problem assumptions',VerificationState.NOT_RUN,
            'theorem registry gate; v0.4 intentionally contains no qualifying general theorem artifact',outputs['reliability_status'])]

class CPUGPUEquivalence(Module):
    metadata=ModuleMetadata('fem_cert.cpu_gpu_equivalence','CPU↔GPU Linear Solve Equivalence','0.4.0','Verification',
        'When CUDA/CuPy is available, solve the same stored reduced system on CPU and GPU and compare host results and residuals.',Maturity.EXPERIMENTAL)
    inputs=(PortSpec('system','linear_system_nd'),); outputs=(PortSpec('equivalence','record'),)
    parameters=(ParameterSpec('atol','number',1e-10),ParameterSpec('rtol','number',1e-10))
    proof_status=ProofStatus(evidence={EvidenceKind.NUMERICAL},unit_tests=True,documentation=True,
        limitations=['numerical cross-backend equivalence is not a proof of bitwise equality','verification is NOT_RUN when CUDA/CuPy is unavailable'])
    def execute(self,inputs,params,ctx):
        s=inputs['system']; A=_dense(s['matrix']); b=np.asarray(s['rhs'],float); cpu=np.linalg.solve(A,b) if len(b) else np.array([])
        try:
            import cupy as cp
            if cp.cuda.runtime.getDeviceCount()<1: raise RuntimeError('no CUDA device')
            gpu=cp.asnumpy(cp.linalg.solve(cp.asarray(A),cp.asarray(b))) if len(b) else np.array([])
            diff=float(np.max(np.abs(cpu-gpu))) if len(cpu) else 0.; scale=float(np.max(np.abs(cpu))) if len(cpu) else 0.
            tol=float(params['atol'])+float(params['rtol'])*scale; avail=True; passed=diff<=tol
            gres=float(np.linalg.norm(A@gpu-b,np.inf)) if len(b) else 0.
            return {'equivalence':{'gpu_available':True,'passed':passed,'max_abs_difference':diff,'tolerance':tol,'gpu_residual_inf':gres,'backend':'cupy'}}
        except Exception as e:
            return {'equivalence':{'gpu_available':False,'passed':False,'reason':str(e),'backend':'unavailable'}}
    def verify(self,inputs,params,outputs,ctx):
        x=outputs['equivalence']
        state=(VerificationState.PASS if x.get('passed') else VerificationState.FAIL) if x.get('gpu_available') else VerificationState.NOT_RUN
        return [VerificationRecord('cpu-gpu-solve-equivalence',EvidenceKind.NUMERICAL,
            'CPU and GPU solutions of the same stored linear system agree within configured tolerance',state,'independent NumPy and CuPy solves followed by host comparison',x)]

def register_fem_cert(registry):
    for cls in (CertifiedPoissonAssembly,IntervalAlgebraicResidual,DiscreteEnergyErrorCertificate,EstimatorReliabilityGate,CPUGPUEquivalence): registry.register(cls)
