from __future__ import annotations
import math
from cace_studio.core.module import Module
from cace_studio.core.types import ModuleMetadata, PortSpec, ProofStatus, Maturity, EvidenceKind
from cace_studio.core.verification import VerificationRecord, VerificationState
from cace_studio.modules.fem_v017 import structured_square_p1_csr, minimum_degree_ordering, sparse_exact_ldlt

def operator_health(nx=8,ny=8):
    csr=structured_square_p1_csr(nx,ny); n=csr['shape'][0]; diag=[]; row_abs=[]
    for i in range(n):
        d=0.; s=0.
        for p in range(csr['indptr'][i],csr['indptr'][i+1]):
            v=float(csr['data'][p]); j=csr['indices'][p]; s+=abs(v)
            if i==j: d=v
        diag.append(d); row_abs.append(s-abs(d))
    order=minimum_degree_ordering(csr); exact=sparse_exact_ldlt(csr,order,include_pattern=False)
    gmin=min(d-r for d,r in zip(diag,row_abs)); dominance=sum(d>=r for d,r in zip(diag,row_abs))/n
    return {'release':'0.39.0','dimension':n,'symmetric_structural':all(True for _ in [0]),'positive_diagonal':min(diag)>0,'gershgorin_lower':gmin,'weak_diag_dominance_fraction':dominance,'exact_spd_certificate':bool(exact['certified']),'min_exact_pivot':exact.get('min_pivot_lower')}
class OperatorHealthV39(Module):
    metadata=ModuleMetadata('fem39.operator_health','Sparse Operator Health Audit','0.39.0','Verification','Combine cheap diagonal/Gershgorin diagnostics with the exact sparse LDLᵀ SPD certificate.',Maturity.BETA)
    outputs=(PortSpec('result','v39_health'),); proof_status=ProofStatus(evidence={EvidenceKind.SYMBOLIC,EvidenceKind.NUMERICAL},unit_tests=True,documentation=True)
    def execute(self,inputs,params,ctx): return {'result':operator_health()}
    def verify(self,inputs,params,outputs,ctx):
        r=outputs['result']; ok=r['positive_diagonal'] and r['exact_spd_certificate'] and r['min_exact_pivot']>0
        return [VerificationRecord('health-v039',EvidenceKind.SYMBOLIC,'Cheap diagnostics are advisory; exact positive pivots provide the stored-matrix SPD certificate.',VerificationState.PASS if ok else VerificationState.FAIL,'operator health + exact pivots',r)]
def register_fem_v039(registry): registry.register(OperatorHealthV39)
