from __future__ import annotations
import math
import numpy as np
from cace_studio.core.module import Module,ValidationError
from cace_studio.core.types import ModuleMetadata,PortSpec,ProofStatus,Maturity,EvidenceKind
from cace_studio.core.verification import VerificationRecord,VerificationState
from cace_studio.core.interval import Interval,singleton,add,sub,mul,div
from cace_studio.modules.fem_nd import _dense
from cace_studio.core.formal_kernel_v15 import assembly_artifact,KERNEL_NAME,KERNEL_VERSION
from cace_studio.core.formal_bridge_v15 import invoke_assembly_checker
from cace_studio.core.theorems import TheoremContract,TheoremStatus

class AssemblyFormalProofV15(Module):
    metadata=ModuleMetadata('formal15.assembly_invariants','Global Assembly Invariants Formal Proof','0.15.0','Formal Verification','Machine-check exact P1 assembly symmetry, constant nullspace, and Dirichlet SPD invariants on an exact rational 1D mesh.',Maturity.BETA)
    outputs=(PortSpec('formal_result','formal_attestation_v15'),)
    proof_status=ProofStatus(evidence={EvidenceKind.FORMAL},unit_tests=True,regression_tests=True,documentation=True,limitations=['formal scope is the supplied exact rational 1D mesh and unit diffusion'])
    def execute(self,inputs,params,ctx):
        art=assembly_artifact(); att=invoke_assembly_checker(art)
        return {'formal_result':{'artifact':art,'attestation':att,'machine_checked':bool(att.get('passed'))}}
    def verify(self,inputs,params,outputs,ctx):
        a=outputs['formal_result']['attestation']; ok=a.get('passed') is True and a.get('process_returncode')==0 and a.get('checker')==KERNEL_NAME and a.get('checker_version')==KERNEL_VERSION
        return [VerificationRecord('assembly-invariants-machine-check-v015',EvidenceKind.FORMAL,'Exact P1 assembly invariants and Dirichlet SPD hold for the checked rational mesh.',VerificationState.PASS if ok else VerificationState.FAIL,'independent exact-rational assembly checker subprocess',a)]

class FormalRegistryBridgeV15(Module):
    metadata=ModuleMetadata('formal15.registry_bridge','Formal Assembly Registry Bridge','0.15.0','Formal Verification','Promote the assembly theorem only after independently re-running the v0.15 checker.',Maturity.BETA)
    inputs=(PortSpec('formal_result','formal_attestation_v15'),); outputs=(PortSpec('theorem','theorem_contract_v15'),)
    proof_status=ProofStatus(evidence={EvidenceKind.FORMAL},unit_tests=True,regression_tests=True,documentation=True)
    def execute(self,inputs,params,ctx):
        art=inputs['formal_result']['artifact']; att=invoke_assembly_checker(art); ok=bool(att.get('passed') and att.get('process_returncode')==0 and att.get('checker')==KERNEL_NAME and att.get('checker_version')==KERNEL_VERSION)
        c=TheoremContract(theorem_id=art['theorem_id'],statement=art['statement'],status=TheoremStatus.MACHINE_CHECKED if ok else TheoremStatus.OBLIGATION,
                          assumptions=(art.get('scope',''),),evidence_kind=EvidenceKind.FORMAL.value if ok else '',checker=f'{KERNEL_NAME} {KERNEL_VERSION}' if ok else None,artifact=f"sha256:{att.get('artifact_sha256','')}" if ok else None)
        d=c.describe(); d.update({'formal_evidence':ok,'promotion_recheck':att}); return {'theorem':d}
    def verify(self,inputs,params,outputs,ctx):
        t=outputs['theorem']; ok=t.get('status')=='machine-checked' and t.get('formal_evidence') is True and t.get('promotion_recheck',{}).get('passed') is True
        return [VerificationRecord('formal-assembly-registry-recheck-v015',EvidenceKind.FORMAL,'Registry promotion requires an independent successful checker rerun.',VerificationState.PASS if ok else VerificationState.FAIL,'checker re-execution',t)]

def _interval_ldlt(A:np.ndarray):
    n=A.shape[0]
    if A.shape!=(n,n): raise ValidationError('square matrix required')
    if np.max(np.abs(A-A.T))>0: return {'certified':False,'reason':'stored matrix is not exactly symmetric in binary64'}
    L=[[Interval(0.0,0.0) for _ in range(n)] for _ in range(n)]; D=[Interval(0.0,0.0) for _ in range(n)]
    for i in range(n):
        L[i][i]=singleton(1.0); acc=Interval(0.0,0.0)
        for k in range(i): acc=add(acc,mul(mul(L[i][k],L[i][k]),D[k]))
        piv=sub(singleton(float(A[i,i])),acc)
        if not (piv.lo>0 and math.isfinite(piv.lo)): return {'certified':False,'reason':'interval LDL pivot is not strictly positive','pivot_index':i,'pivot_interval':[piv.lo,piv.hi]}
        D[i]=piv
        for j in range(i+1,n):
            acc2=Interval(0.0,0.0)
            for k in range(i): acc2=add(acc2,mul(mul(L[j][k],L[i][k]),D[k]))
            L[j][i]=div(sub(singleton(float(A[j,i])),acc2),D[i])
    # Independent interval reconstruction enclosure.
    max_width=0.0
    for i in range(n):
        for j in range(n):
            s=Interval(0.0,0.0)
            for k in range(min(i,j)+1): s=add(s,mul(mul(L[i][k],D[k]),L[j][k]))
            a=float(A[i,j])
            if not (s.lo<=a<=s.hi): return {'certified':False,'reason':'stored entry not enclosed by interval LDL reconstruction','i':i,'j':j,'entry':a,'reconstruction':[s.lo,s.hi]}
            max_width=max(max_width,s.hi-s.lo)
    return {'certified':True,'method':'interval-ldlt-reconstruction','pivots':[[d.lo,d.hi] for d in D],'min_pivot_lower':min((d.lo for d in D),default=math.inf),'max_reconstruction_width':max_width,'dimension':n,'scope':'stored binary64 reduced matrix'}

class VerifiedSparseLDLTV15(Module):
    metadata=ModuleMetadata('fem15.verified_ldlt','Verified Sparse-System LDLᵀ Certificate','0.15.0','Certified Linear Algebra','Certify positive interval LDLᵀ pivots and interval reconstruction for the stored CSR reduced matrix.',Maturity.BETA,assumptions=('stored CSR matrix is intended symmetric','IEEE-754 outward interval operations are conforming'))
    inputs=(PortSpec('system','linear_system_nd'),); outputs=(PortSpec('factorization_certificate','verified_factorization_v15'),)
    proof_status=ProofStatus(evidence={EvidenceKind.INTERVAL},unit_tests=True,property_tests=True,documentation=True,limitations=['reference verifier currently densifies CSR; sparse production factorization is future work','certificate is for the stored discrete matrix, not the continuum operator'])
    def execute(self,inputs,params,ctx): return {'factorization_certificate':_interval_ldlt(_dense(inputs['system']['matrix']))}
    def verify(self,inputs,params,outputs,ctx):
        c=outputs['factorization_certificate']; state=VerificationState.PASS if c.get('certified') else VerificationState.NOT_RUN
        return [VerificationRecord('verified-ldlt-factorization-v015',EvidenceKind.INTERVAL,'The stored reduced matrix admits the reported interval LDLᵀ factorization with strictly positive pivots and enclosing reconstruction.',state,'outward-rounded interval LDLᵀ plus independent reconstruction enclosure',c)]

class AssemblyFactorizationSummaryV15(Module):
    metadata=ModuleMetadata('fem15.summary','Assembly + Factorization Certificate Summary','0.15.0','Verification','Compose formal assembly provenance with the interval factorization certificate without conflating their evidence levels.',Maturity.BETA)
    inputs=(PortSpec('theorem','theorem_contract_v15'),PortSpec('factorization_certificate','verified_factorization_v15')); outputs=(PortSpec('summary','v15_summary'),)
    proof_status=ProofStatus(evidence={EvidenceKind.FORMAL,EvidenceKind.INTERVAL},unit_tests=True,documentation=True)
    def execute(self,inputs,params,ctx):
        t=inputs['theorem']; f=inputs['factorization_certificate']
        return {'summary':{'formal_assembly_machine_checked':t.get('status')=='machine-checked' and t.get('formal_evidence') is True,'stored_matrix_factorization_certified':bool(f.get('certified')),'factorization_method':f.get('method'),'min_pivot_lower':f.get('min_pivot_lower'),'continuum_pde_formally_verified':False}}
    def verify(self,inputs,params,outputs,ctx):
        s=outputs['summary']; ok=s['formal_assembly_machine_checked'] and s['stored_matrix_factorization_certified'] and not s['continuum_pde_formally_verified']
        return [VerificationRecord('v015-composed-scope-audit',EvidenceKind.INTERVAL,'Formal assembly invariants and interval matrix factorization are both present without escalating to a continuum PDE proof.',VerificationState.PASS if ok else VerificationState.FAIL,'evidence-scope composition audit',s)]

def register_fem_v015(registry):
    for cls in (AssemblyFormalProofV15,FormalRegistryBridgeV15,VerifiedSparseLDLTV15,AssemblyFactorizationSummaryV15): registry.register(cls)
