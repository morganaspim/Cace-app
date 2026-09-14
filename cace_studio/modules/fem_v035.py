from __future__ import annotations
from cace_studio.core.module import Module
from cace_studio.core.types import ModuleMetadata, PortSpec, ProofStatus, Maturity, EvidenceKind
from cace_studio.core.verification import VerificationRecord, VerificationState
from cace_studio.modules.fem_v026 import reproducibility_signature
from cace_studio.modules.fem_v027 import mixed_precision_refinement
from cace_studio.modules.fem_v028 import checkpoint_campaign
from cace_studio.modules.fem_v029 import matrix_diagnostics
from cace_studio.modules.fem_v030 import multi_rhs_campaign
from cace_studio.modules.fem_v031 import stress_3d
from cace_studio.modules.fem_v033 import provenance_bundle
from cace_studio.modules.fem_v034 import fault_injection_suite

def consolidated_v035():
    parts={'repro':reproducibility_signature(8,8),'mixed_precision':mixed_precision_refinement(6,6,2),'checkpoints':checkpoint_campaign(),'diagnostics':matrix_diagnostics(8,8),'multi_rhs':multi_rhs_campaign(6,6,3),'discrete_3d':stress_3d(4),'provenance':provenance_bundle(),'faults':fault_injection_suite()}
    checks={
      'reproducible':parts['repro']['stable'], 'refinement_ok':parts['mixed_precision']['final_residual']<=1e-9,
      'checkpoint_tamper_detection':parts['checkpoints']['tamper_detected'], 'matrix_health':parts['diagnostics']['symmetric'] and parts['diagnostics']['positive_diagonal'],
      'multi_rhs_ok':parts['multi_rhs']['max_residual_inf']<=1e-10, 'discrete_3d_exact':parts['discrete_3d']['certified'],
      'provenance_verified':parts['provenance']['verified'], 'fault_refusal':parts['faults']['all_faults_detected']}
    return {'release':'0.35.0','parts':parts,'checks':checks,'all_checks_pass':all(checks.values()),'evidence_boundary':{'formal_continuum_pde':False,'exact_sparse_discrete':'symbolic/exact','native_numeric':'numerical','provenance':'cryptographic-content-integrity'}}

class ConsolidatedCampaignV35(Module):
    metadata=ModuleMetadata('fem35.consolidated','v0.35 Consolidated Verification Campaign','0.35.0','Verification','Compose reproducibility, refinement, recovery, diagnostics, multi-RHS, 3D discrete stress, provenance and refusal tests.',Maturity.BETA)
    outputs=(PortSpec('result','v35_campaign'),)
    proof_status=ProofStatus(evidence={EvidenceKind.NUMERICAL,EvidenceKind.SYMBOLIC},unit_tests=True,regression_tests=True,documentation=True,limitations=['consolidation does not promote discrete evidence into a continuum PDE proof','portfolio timing is intentionally excluded from deterministic pass/fail campaign'])
    def execute(self,inputs,params,ctx): return {'result':consolidated_v035()}
    def verify(self,inputs,params,outputs,ctx):
        r=outputs['result']; ok=r['all_checks_pass'] and not r['evidence_boundary']['formal_continuum_pde']
        return [VerificationRecord('campaign-v035',EvidenceKind.SYMBOLIC,'All deterministic v0.26-v0.35 verification gates pass while the continuum-theorem boundary remains explicit.',VerificationState.PASS if ok else VerificationState.FAIL,'cross-release deterministic campaign',r['checks'])]

def register_fem_v035(registry): registry.register(ConsolidatedCampaignV35)
