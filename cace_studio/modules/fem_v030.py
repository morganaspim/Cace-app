from __future__ import annotations
import numpy as np
from cace_studio.core.module import Module
from cace_studio.core.types import ModuleMetadata, PortSpec, ParameterSpec, ProofStatus, Maturity, EvidenceKind
from cace_studio.core.verification import VerificationRecord, VerificationState
from cace_studio.core.native_runtime import NativeRuntime
from cace_studio.modules.fem_v017 import structured_square_p1_csr, sparse_exact_ldlt
from cace_studio.modules.fem_v018 import choose_orderings, matvec
from cace_studio.modules.fem_v027 import dense_from_csr

def multi_rhs_campaign(nx=8,ny=8,nrhs=4):
    csr=structured_square_p1_csr(nx,ny); orders,_,winner=choose_orderings(csr,nx,ny); order=orders[winner]; exact=sparse_exact_ldlt(csr,order)
    rt=NativeRuntime(); results=[]
    A=dense_from_csr(csr,np.float64)
    for q in range(nrhs):
        xt=[1.0+(((q+3)*17*i+q)%29)/53.0 for i in range(csr['shape'][0])]; b=matvec(csr,xt)
        if rt.status.available:
            sol=rt.sparse_ldlt_solve(csr,order,b); x=sol['x']; backend='cpp20-cabi'
        else:
            x=np.linalg.solve(A,np.asarray(b)).tolist(); backend='numpy-fallback'
        err=max((abs(a-bb) for a,bb in zip(x,xt)),default=0.0); resid=max((abs(a-bb) for a,bb in zip(matvec(csr,x),b)),default=0.0)
        results.append({'rhs':q,'max_solution_error':err,'residual_inf':resid})
    return {'release':'0.30.0','dimension':csr['shape'][0],'rhs_count':nrhs,'backend':backend,'exact_structure_certified':bool(exact.get('certified')),'max_solution_error':max(r['max_solution_error'] for r in results),'max_residual_inf':max(r['residual_inf'] for r in results),'results':results}

class MultiRHSSolveV30(Module):
    metadata=ModuleMetadata('fem30.multi_rhs','Multi-RHS Sparse Solve Campaign','0.30.0','Runtime','Exercise one certified sparse structure against multiple deterministic right-hand sides.',Maturity.BETA)
    parameters=(ParameterSpec('nx','integer',8),ParameterSpec('ny','integer',8),ParameterSpec('nrhs','integer',4)); outputs=(PortSpec('result','v30_multi_rhs'),)
    proof_status=ProofStatus(evidence={EvidenceKind.NUMERICAL,EvidenceKind.SYMBOLIC},unit_tests=True,documentation=True,limitations=['numeric solution accuracy is empirical','fallback uses dense NumPy when native runtime is unavailable'])
    def execute(self,inputs,params,ctx): return {'result':multi_rhs_campaign(int(params['nx']),int(params['ny']),int(params['nrhs']))}
    def verify(self,inputs,params,outputs,ctx):
        r=outputs['result']; ok=r['exact_structure_certified'] and r['max_solution_error']<=1e-10 and r['max_residual_inf']<=1e-10
        return [VerificationRecord('multi-rhs-v030',EvidenceKind.NUMERICAL,'All deterministic RHS solves satisfy solution/residual tolerances on an exactly certified sparse structure.',VerificationState.PASS if ok else VerificationState.FAIL,'multi-RHS solve regression',r)]

def register_fem_v030(registry): registry.register(MultiRHSSolveV30)
