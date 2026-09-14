from __future__ import annotations
import numpy as np
from cace_studio.core.module import Module
from cace_studio.core.types import ModuleMetadata, PortSpec, ParameterSpec, ProofStatus, Maturity, EvidenceKind
from cace_studio.core.verification import VerificationRecord, VerificationState
from cace_studio.modules.fem_v017 import structured_square_p1_csr, sparse_exact_ldlt
from cace_studio.modules.fem_v018 import choose_orderings, matvec

def dense_from_csr(csr,dtype=float):
    n=csr['shape'][0]; A=np.zeros((n,n),dtype=dtype)
    for i in range(n):
        for p in range(csr['indptr'][i],csr['indptr'][i+1]): A[i,csr['indices'][p]]=csr['data'][p]
    return A

def mixed_precision_refinement(nx=7,ny=7,steps=3):
    csr=structured_square_p1_csr(nx,ny); A64=dense_from_csr(csr,np.float64); A32=A64.astype(np.float32)
    n=A64.shape[0]; xtrue=np.array([1.0+((13*i)%17)/37.0 for i in range(n)],dtype=np.float64); b=A64@xtrue
    x=np.linalg.solve(A32,b.astype(np.float32)).astype(np.float64)
    hist=[]
    for k in range(max(0,int(steps))+1):
        r=b-A64@x; hist.append(float(np.linalg.norm(r,ord=np.inf)))
        if k<int(steps): x += np.linalg.solve(A32,r.astype(np.float32)).astype(np.float64)
    orders,_,winner=choose_orderings(csr,nx,ny); exact=sparse_exact_ldlt(csr,orders[winner])
    return {'release':'0.27.0','dimension':n,'residual_history':hist,'initial_residual':hist[0],'final_residual':hist[-1],'max_solution_error':float(np.max(np.abs(x-xtrue))),'improved':hist[-1] <= hist[0]+1e-30,'exact_structure_certified':bool(exact.get('certified') and exact.get('exact_reconstruction')),'scope':'mixed-precision numerical refinement backed by separate exact structural certificate'}

class MixedPrecisionRefinementV27(Module):
    metadata=ModuleMetadata('fem27.mixed_precision','Mixed-Precision Iterative Refinement','0.27.0','Runtime','Use float32 factor solves with float64 residual correction and retain the exact sparse structural oracle.',Maturity.BETA)
    parameters=(ParameterSpec('nx','integer',7),ParameterSpec('ny','integer',7),ParameterSpec('steps','integer',3)); outputs=(PortSpec('result','v27_refinement'),)
    proof_status=ProofStatus(evidence={EvidenceKind.NUMERICAL,EvidenceKind.SYMBOLIC},unit_tests=True,documentation=True,limitations=['dense NumPy float32 solve is a reference mixed-precision kernel','convergence is empirical for the tested matrix'])
    def execute(self,inputs,params,ctx): return {'result':mixed_precision_refinement(int(params['nx']),int(params['ny']),int(params['steps']))}
    def verify(self,inputs,params,outputs,ctx):
        r=outputs['result']; ok=r['improved'] and r['final_residual']<=1e-9 and r['exact_structure_certified']
        return [VerificationRecord('mixed-precision-v027',EvidenceKind.NUMERICAL,'Iterative refinement reduces/retains residual to tolerance while the matrix structure retains an exact sparse factor certificate.',VerificationState.PASS if ok else VerificationState.FAIL,'float32 correction + float64 residual',r)]

def register_fem_v027(registry): registry.register(MixedPrecisionRefinementV27)
