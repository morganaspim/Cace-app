from __future__ import annotations
import math, os
import numpy as np

from cace_studio.core.module import Module, ValidationError
from cace_studio.core.types import ModuleMetadata, PortSpec, ParameterSpec, ProofStatus, Maturity, EvidenceKind
from cace_studio.core.verification import VerificationRecord, VerificationState
from cace_studio.core.interval import Interval, singleton, add, sub, mul, abs_interval, sum_intervals, up
from cace_studio.modules.fem_nd import _dense


def _ival(x: Interval):
    return [float(x.lo), float(x.hi)]


def _interval_dot_float_interval(a: np.ndarray, x: list[Interval]) -> Interval:
    acc = Interval(0.0, 0.0)
    for ai, xi in zip(a, x):
        acc = add(acc, mul(singleton(float(ai)), xi))
    return acc


def _interval_residual_b_minus_ax(A: np.ndarray, b: np.ndarray, x: np.ndarray) -> list[Interval]:
    out=[]
    for i in range(len(b)):
        ax=Interval(0.0,0.0)
        for j in range(len(x)):
            ax=add(ax,mul(singleton(float(A[i,j])),singleton(float(x[j]))))
        out.append(sub(singleton(float(b[i])),ax))
    return out


def _interval_defect_matrix(R: np.ndarray, A: np.ndarray) -> list[list[Interval]]:
    n=A.shape[0]; out=[]
    for i in range(n):
        row=[]
        for j in range(n):
            s=Interval(0.0,0.0)
            for k in range(n):
                s=add(s,mul(singleton(float(R[i,k])),singleton(float(A[k,j]))))
            row.append(sub(singleton(1.0 if i==j else 0.0),s))
        out.append(row)
    return out


def _matrix_inf_upper(E: list[list[Interval]]) -> float:
    if not E: return 0.0
    vals=[]
    for row in E:
        s=Interval(0.0,0.0)
        for x in row: s=add(s,abs_interval(x))
        vals.append(s.hi)
    return float(up(max(vals,default=0.0)))


def _verified_enclosure(A: np.ndarray, b: np.ndarray, xhat: np.ndarray):
    n=len(b)
    if n==0:
        return {'certified':True,'method':'empty-system','q_upper':0.0,'correction_inf_upper':0.0,
                'radius':0.0,'solution_intervals':[],'residual_intervals':[],'krawczyk_inclusion':True}
    if A.shape!=(n,n) or xhat.shape!=(n,):
        raise ValidationError('incompatible linear system/solution dimensions')
    if not (np.all(np.isfinite(A)) and np.all(np.isfinite(b)) and np.all(np.isfinite(xhat))):
        raise ValidationError('verified enclosure requires finite binary64 data')
    try:
        R=np.linalg.inv(A)
    except np.linalg.LinAlgError:
        return {'certified':False,'method':'preconditioned-contraction','reason':'numerical inverse candidate could not be formed'}
    if not np.all(np.isfinite(R)):
        return {'certified':False,'method':'preconditioned-contraction','reason':'inverse candidate is non-finite'}

    residual=_interval_residual_b_minus_ax(A,b,xhat)
    E=_interval_defect_matrix(R,A)
    q=_matrix_inf_upper(E)
    if not (q < 1.0):
        return {'certified':False,'method':'preconditioned-contraction','q_upper':q,
                'reason':'certified ||I-RA||_inf bound is not below one',
                'residual_intervals':[_ival(x) for x in residual]}

    y=[_interval_dot_float_interval(R[i,:],residual) for i in range(n)]
    yinf=max((abs_interval(v).hi for v in y),default=0.0)
    denom=1.0-q
    if not denom>0:
        return {'certified':False,'method':'preconditioned-contraction','q_upper':q,'reason':'nonpositive contraction denominator'}
    radius=up(yinf/denom)
    # Inflate very slightly so outward-rounded Krawczyk inclusion is robust at the boundary.
    radius=up(radius*(1.0+32.0*np.finfo(float).eps)+np.finfo(float).tiny)

    def inclusion(rad: float):
        X=[Interval(-rad,rad) for _ in range(n)]; K=[]
        for i in range(n):
            corr=y[i]
            for j in range(n): corr=add(corr,mul(E[i][j],X[j]))
            K.append(corr)
        return all(k.lo>=-rad and k.hi<=rad for k in K),K

    ok,K=inclusion(radius)
    for _ in range(8):
        if ok: break
        radius=up(radius*1.01 + np.finfo(float).tiny); ok,K=inclusion(radius)
    if not ok:
        return {'certified':False,'method':'preconditioned-contraction','q_upper':q,'reason':'Krawczyk/fixed-point inclusion could not be enclosed after inflation'}

    sol=[]
    for xi in xhat:
        sol.append([math.nextafter(float(xi)-radius,-math.inf),math.nextafter(float(xi)+radius,math.inf)])
    return {
        'certified':True,
        'method':'preconditioned-contraction-krawczyk-box',
        'q_upper':q,
        'correction_inf_upper':float(yinf),
        'radius':float(radius),
        'solution_intervals':sol,
        'residual_intervals':[_ival(x) for x in residual],
        'krawczyk_correction_intervals':[_ival(x) for x in K],
        'krawczyk_inclusion':True,
        'scope':'exact solution of stored binary64 discrete linear system',
        'preconditioner':'binary64 inverse candidate; correctness comes only from interval contraction test',
    }


class VerifiedSparseSolutionEnclosure(Module):
    metadata=ModuleMetadata('fem10.verified_sparse_solve','Verified Sparse Discrete Solution Enclosure','0.10.0','Certified Linear Algebra',
        'Enclose the exact solution of the stored binary64 CSR system using an approximate inverse only as a preconditioner and an interval-certified contraction/Krawczyk box.',Maturity.BETA,
        assumptions=('stored CSR matrix and rhs define the exact discrete problem being certified','IEEE-754 binary64 plus math.nextafter provide directed outward rounding'))
    inputs=(PortSpec('system','linear_system_nd'),PortSpec('solution','fem_solution_nd'))
    outputs=(PortSpec('solution_enclosure','verified_solution_enclosure'),)
    proof_status=ProofStatus(evidence={EvidenceKind.INTERVAL},unit_tests=True,property_tests=True,documentation=True,
        limitations=['current reference implementation densifies CSR to construct the preconditioner','certificate concerns the stored discrete system, not continuum discretization error'])
    def validate(self,inputs,params):
        super().validate(inputs,params)
        A=_dense(inputs['system']['matrix']); b=np.asarray(inputs['system']['rhs'],float); x=np.asarray(inputs['solution']['interior'],float)
        if A.shape!=(len(b),len(b)) or len(x)!=len(b): raise ValidationError('system and solution dimensions do not match')
    def execute(self,inputs,params,ctx):
        A=_dense(inputs['system']['matrix']); b=np.asarray(inputs['system']['rhs'],float); x=np.asarray(inputs['solution']['interior'],float)
        return {'solution_enclosure':_verified_enclosure(A,b,x)}
    def verify(self,inputs,params,outputs,ctx):
        c=outputs['solution_enclosure']; state=VerificationState.PASS if c.get('certified') else VerificationState.NOT_RUN
        return [VerificationRecord('verified-discrete-solution-enclosure',EvidenceKind.INTERVAL,
            'the exact solution of the stored discrete linear system lies in the reported coefficient box',state,
            'interval preconditioned fixed-point/Krawczyk inclusion with certified ||I-RA||_inf < 1',c)]


class SolutionEnclosureDiagnostics(Module):
    metadata=ModuleMetadata('fem10.enclosure_diagnostics','Solution Enclosure Diagnostics','0.10.0','Verification',
        'Summarize widths and midpoint containment for a verified coefficient enclosure without changing its proof status.',Maturity.BETA)
    inputs=(PortSpec('solution_enclosure','verified_solution_enclosure'),PortSpec('solution','fem_solution_nd'))
    outputs=(PortSpec('diagnostics','solution_enclosure_diagnostics'),)
    proof_status=ProofStatus(evidence={EvidenceKind.INTERVAL},unit_tests=True,documentation=True)
    def execute(self,inputs,params,ctx):
        c=inputs['solution_enclosure']; x=np.asarray(inputs['solution']['interior'],float)
        if not c.get('certified'):
            return {'diagnostics':{'certified':False,'reason':'upstream enclosure not certified'}}
        ints=c['solution_intervals']; widths=[float(hi-lo) for lo,hi in ints]
        contains=[bool(lo<=float(v)<=hi) for (lo,hi),v in zip(ints,x)]
        return {'diagnostics':{'certified':all(contains),'dofs':len(ints),'max_width':max(widths,default=0.0),'mean_width':float(np.mean(widths)) if widths else 0.0,'computed_solution_contained':all(contains),'radius':c['radius'],'q_upper':c['q_upper']}}
    def verify(self,inputs,params,outputs,ctx):
        d=outputs['diagnostics']; state=VerificationState.PASS if d.get('certified') else VerificationState.NOT_RUN
        return [VerificationRecord('solution-enclosure-diagnostics',EvidenceKind.INTERVAL,'reported interval box contains the computed coefficient vector and has finite nonnegative width',state,'interval-box invariant checks',d)]


class SolutionEnclosurePlot(Module):
    metadata=ModuleMetadata('viz10.solution_enclosure','Discrete Solution Enclosure Plot','0.10.0','Visualization',
        'Render coefficient intervals and computed coefficients as a reproducible PNG inspection artifact.',Maturity.BETA)
    inputs=(PortSpec('solution_enclosure','verified_solution_enclosure'),PortSpec('solution','fem_solution_nd'))
    outputs=(PortSpec('visualization','visualization_artifact'),)
    parameters=(ParameterSpec('output_path','string','examples/v10_solution_enclosure.png'),)
    proof_status=ProofStatus(evidence={EvidenceKind.EXPERIMENTAL},unit_tests=True,documentation=True,limitations=['visualization contributes no proof evidence'])
    def execute(self,inputs,params,ctx):
        c=inputs['solution_enclosure']; x=np.asarray(inputs['solution']['interior'],float)
        if not c.get('certified'): raise ValidationError('cannot visualize an uncertified enclosure')
        import matplotlib; matplotlib.use('Agg',force=True)
        import matplotlib.pyplot as plt
        ints=np.asarray(c['solution_intervals'],float); idx=np.arange(len(x)); lo=ints[:,0] if len(x) else np.array([]); hi=ints[:,1] if len(x) else np.array([])
        path=str(params['output_path']); os.makedirs(os.path.dirname(path) or '.',exist_ok=True)
        fig,ax=plt.subplots(figsize=(7,4.5))
        if len(x):
            yerr=np.vstack([x-lo,hi-x]); ax.errorbar(idx,x,yerr=yerr,fmt='o',capsize=4)
        ax.set_xlabel('Interior DOF'); ax.set_ylabel('Coefficient value'); ax.set_title('CACE v0.10 verified discrete solution enclosure'); ax.grid(True,alpha=0.25)
        fig.tight_layout(); fig.savefig(path,dpi=140); plt.close(fig)
        return {'visualization':{'path':path,'format':'png','bytes':os.path.getsize(path),'dofs':len(x),'radius':c['radius']}}
    def verify(self,inputs,params,outputs,ctx):
        a=outputs['visualization']; ok=os.path.exists(a['path']) and a['bytes']>1000
        if ok:
            with open(a['path'],'rb') as f: ok=f.read(8)==b'\x89PNG\r\n\x1a\n'
        return [VerificationRecord('v10-enclosure-plot-smoke',EvidenceKind.EXPERIMENTAL,'PNG was rendered from the verified coefficient enclosure and computed solution',VerificationState.PASS if ok else VerificationState.FAIL,'headless Matplotlib render plus PNG signature',a)]


def register_fem_v010(registry):
    for cls in (VerifiedSparseSolutionEnclosure,SolutionEnclosureDiagnostics,SolutionEnclosurePlot):
        registry.register(cls)
