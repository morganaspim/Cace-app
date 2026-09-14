from __future__ import annotations
from cace_studio.core.module import Module, ValidationError
from cace_studio.core.types import ModuleMetadata, PortSpec, ParameterSpec, ProofStatus, Maturity, EvidenceKind
from cace_studio.core.verification import VerificationRecord, VerificationState
from cace_studio.modules.fem_v017 import sparse_exact_ldlt, minimum_degree_ordering, symbolic_elimination

def structured_3d_poisson_csr(n=4):
    if n<2: raise ValidationError('n must be >= 2')
    m=n-1; N=m*m*m
    def idx(i,j,k): return (k*m+j)*m+i
    rows=[{} for _ in range(N)]
    for k in range(m):
      for j in range(m):
       for i in range(m):
        r=idx(i,j,k); rows[r][r]=6.0
        for di,dj,dk in ((1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1)):
            a,b,c=i+di,j+dj,k+dk
            if 0<=a<m and 0<=b<m and 0<=c<m: rows[r][idx(a,b,c)]=-1.0
    data=[];indices=[];indptr=[0]
    for r in rows:
        for j in sorted(r): indices.append(j); data.append(r[j])
        indptr.append(len(data))
    return {'shape':[N,N],'data':data,'indices':indices,'indptr':indptr,'meta':{'grid_n':n,'interior_dofs':N,'operator':'7-point discrete Poisson'}}

def stress_3d(n=4):
    csr=structured_3d_poisson_csr(n); natural=symbolic_elimination(csr); order=minimum_degree_ordering(csr); ordered=symbolic_elimination(csr,order); exact=sparse_exact_ldlt(csr,order)
    return {'release':'0.31.0','dimension':csr['shape'][0],'input_nnz':len(csr['data']),'natural_fill':natural['fill_edges'],'ordered_fill':ordered['fill_edges'],'factor_nnz':exact.get('factor_nnz'),'certified':bool(exact.get('certified') and exact.get('exact_reconstruction')),'scope':'3D seven-point discrete Poisson operator; not tetrahedral FEM continuum verification'}

class Discrete3DStressV31(Module):
    metadata=ModuleMetadata('fem31.discrete_3d_stress','3D Discrete Poisson Sparse Stress','0.31.0','Benchmark','Stress sparse ordering and exact LDLᵀ on a structured 3D seven-point discrete Poisson operator.',Maturity.BETA)
    parameters=(ParameterSpec('n','integer',4),); outputs=(PortSpec('result','v31_3d_stress'),)
    proof_status=ProofStatus(evidence={EvidenceKind.SYMBOLIC,EvidenceKind.NUMERICAL},unit_tests=True,documentation=True,limitations=['discrete seven-point operator, not a tetrahedral FEM theorem'])
    def execute(self,inputs,params,ctx): return {'result':stress_3d(int(params['n']))}
    def verify(self,inputs,params,outputs,ctx):
        r=outputs['result']; ok=r['certified'] and r['ordered_fill']<=r['natural_fill']
        return [VerificationRecord('3d-stress-v031',EvidenceKind.SYMBOLIC,'3D discrete operator retains exact sparse LDLᵀ reconstruction after deterministic fill-reducing ordering.',VerificationState.PASS if ok else VerificationState.FAIL,'3D discrete sparse stress',r)]

def register_fem_v031(registry): registry.register(Discrete3DStressV31)
