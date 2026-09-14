from __future__ import annotations
import math
from cace_studio.core.module import Module
from cace_studio.core.types import ModuleMetadata, PortSpec, ParameterSpec, ProofStatus, Maturity, EvidenceKind
from cace_studio.core.verification import VerificationRecord, VerificationState
from cace_studio.modules.fem_v017 import structured_square_p1_csr, _csr_entries

def matrix_diagnostics(nx=10,ny=10):
    csr=structured_square_p1_csr(nx,ny); rows=_csr_entries(csr); n=len(rows)
    diag=[]; radii=[]; sym=True
    for i,r in enumerate(rows):
        d=float(r.get(i,0.0)); rad=sum(abs(float(v)) for j,v in r.items() if j!=i); diag.append(d); radii.append(rad)
        for j,v in r.items():
            if abs(float(v)-float(rows[j].get(i,0.0)))>1e-13: sym=False
    lower=min((d-r for d,r in zip(diag,radii)),default=0.0); upper=max((d+r for d,r in zip(diag,radii)),default=0.0)
    scale=[1.0/math.sqrt(d) if d>0 else 0.0 for d in diag]
    row_abs=[]
    for i,r in enumerate(rows): row_abs.append(sum(abs(float(v))*scale[i]*scale[j] for j,v in r.items()))
    return {'release':'0.29.0','dimension':n,'symmetric':sym,'positive_diagonal':all(d>0 for d in diag),'gershgorin_lower':lower,'gershgorin_upper':upper,'jacobi_scaled_inf_norm':max(row_abs,default=0.0),'diagonal_min':min(diag,default=0.0),'diagonal_max':max(diag,default=0.0),'scope':'diagnostics/proxies only; Gershgorin lower bound may be nonpositive for an SPD matrix'}

class MatrixDiagnosticsV29(Module):
    metadata=ModuleMetadata('fem29.matrix_diagnostics','Sparse Matrix Health Diagnostics','0.29.0','Diagnostics','Report symmetry, positive diagonal, Gershgorin enclosure and Jacobi-scaled norm proxies.',Maturity.BETA)
    parameters=(ParameterSpec('nx','integer',10),ParameterSpec('ny','integer',10)); outputs=(PortSpec('result','v29_diagnostics'),)
    proof_status=ProofStatus(evidence={EvidenceKind.NUMERICAL,EvidenceKind.SYMBOLIC},unit_tests=True,documentation=True,limitations=['conditioning metrics are diagnostics, not a certified condition number'])
    def execute(self,inputs,params,ctx): return {'result':matrix_diagnostics(int(params['nx']),int(params['ny']))}
    def verify(self,inputs,params,outputs,ctx):
        r=outputs['result']; ok=r['symmetric'] and r['positive_diagonal'] and r['gershgorin_upper']>0
        return [VerificationRecord('diagnostics-v029',EvidenceKind.SYMBOLIC,'Stored FEM matrix passes structural symmetry/diagonal health checks; conditioning values remain labeled diagnostics.',VerificationState.PASS if ok else VerificationState.FAIL,'CSR structural diagnostics',r)]

def register_fem_v029(registry): registry.register(MatrixDiagnosticsV29)
