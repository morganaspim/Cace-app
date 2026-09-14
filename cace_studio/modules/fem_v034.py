from __future__ import annotations
import copy
from cace_studio.core.module import Module
from cace_studio.core.types import ModuleMetadata, PortSpec, ProofStatus, Maturity, EvidenceKind
from cace_studio.core.verification import VerificationRecord, VerificationState
from cace_studio.modules.fem_v017 import structured_square_p1_csr, sparse_exact_ldlt, minimum_degree_ordering
from cace_studio.modules.fem_v033 import provenance_bundle, verify_bundle

def fault_injection_suite():
    csr=structured_square_p1_csr(6,6); order=minimum_degree_ordering(csr); baseline=sparse_exact_ldlt(csr,order)
    asym=copy.deepcopy(csr); asym['data'][1]=float(asym['data'][1])+0.125; rejected_asym=not sparse_exact_ldlt(asym,order).get('certified',False)
    indef=copy.deepcopy(csr)
    # Force the first diagonal strongly negative while preserving sparsity.
    p0=next(p for p in range(indef['indptr'][0],indef['indptr'][1]) if indef['indices'][p]==0); indef['data'][p0]=-abs(indef['data'][p0])-10.0
    rejected_indef=not sparse_exact_ldlt(indef,order).get('certified',False)
    bundle=provenance_bundle(); bad=copy.deepcopy(bundle['items']); bad['diagnostics']['dimension']+=1; rejected_bundle=not verify_bundle(bad,bundle['manifest'])
    return {'release':'0.34.0','baseline_certified':bool(baseline.get('certified')),'asymmetry_rejected':rejected_asym,'indefinite_rejected':rejected_indef,'tampered_bundle_rejected':rejected_bundle,'all_faults_detected':rejected_asym and rejected_indef and rejected_bundle}

class FaultInjectionV34(Module):
    metadata=ModuleMetadata('fem34.fault_injection','Certificate Fault-Injection Suite','0.34.0','Verification','Deliberately corrupt matrix/provenance inputs and require the verification paths to refuse them.',Maturity.BETA)
    outputs=(PortSpec('result','v34_faults'),)
    proof_status=ProofStatus(evidence={EvidenceKind.SYMBOLIC},unit_tests=True,regression_tests=True,documentation=True,limitations=['fault suite samples declared corruption classes; it is not exhaustive adversarial verification'])
    def execute(self,inputs,params,ctx): return {'result':fault_injection_suite()}
    def verify(self,inputs,params,outputs,ctx):
        r=outputs['result']; ok=r['baseline_certified'] and r['all_faults_detected']
        return [VerificationRecord('faults-v034',EvidenceKind.SYMBOLIC,'Verifier refuses injected asymmetry, nonpositive factorization and provenance tampering.',VerificationState.PASS if ok else VerificationState.FAIL,'negative-test campaign',r)]

def register_fem_v034(registry): registry.register(FaultInjectionV34)
