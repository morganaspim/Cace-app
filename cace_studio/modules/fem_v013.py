from __future__ import annotations
from cace_studio.core.module import Module, ValidationError
from cace_studio.core.types import ModuleMetadata, PortSpec, ParameterSpec, ProofStatus, Maturity, EvidenceKind
from cace_studio.core.verification import VerificationRecord, VerificationState
from cace_studio.core.formal_kernel import canonical_artifact, KERNEL_NAME, KERNEL_VERSION
from cace_studio.core.formal_bridge import invoke_formal_checker
from cace_studio.core.theorems import TheoremContract, TheoremStatus

class ReferenceSimplexFormalProof(Module):
    metadata=ModuleMetadata('formal13.reference_simplex_barycentric','Reference Simplex Barycentric Formal Proof','0.13.0','Formal Verification',
        'Generate and independently machine-check an exact proof artifact for P1 barycentric partition of unity and Kronecker nodal identities on a canonical reference simplex.',Maturity.BETA,
        assumptions=('canonical reference simplex','dimension is 1, 2, or 3','affine P1 basis encoded with exact rational coefficients'))
    outputs=(PortSpec('formal_result','formal_attestation_v13'),)
    parameters=(ParameterSpec('dimension','integer',2),)
    proof_status=ProofStatus(evidence={EvidenceKind.FORMAL},unit_tests=True,property_tests=True,regression_tests=True,documentation=True,
        formal_artifact='generated exact-rational proof artifact',limitations=['formal result is scoped only to the canonical reference-simplex affine identities','does not prove Poisson reliability or continuum PDE theorems'])
    def validate(self,inputs,params):
        super().validate(inputs,params); d=int(self.resolved_params(params)['dimension'])
        if d not in (1,2,3): raise ValidationError('formal13 supports dimensions 1, 2, and 3')
    def execute(self,inputs,params,ctx):
        artifact=canonical_artifact(int(params['dimension'])); att=invoke_formal_checker(artifact)
        return {'formal_result':{'artifact':artifact,'attestation':att,'machine_checked':bool(att.get('passed')),
            'checker':KERNEL_NAME,'checker_version':KERNEL_VERSION}}
    def verify(self,inputs,params,outputs,ctx):
        r=outputs['formal_result']; a=r['attestation']
        trusted=(a.get('passed') is True and a.get('process_returncode')==0 and a.get('checker')==KERNEL_NAME and a.get('checker_version')==KERNEL_VERSION
                 and sorted(a.get('claims_checked',[]))==['kronecker-nodal-identity','partition-of-unity'])
        return [VerificationRecord('reference-simplex-barycentric-machine-check-v013',EvidenceKind.FORMAL,
            'Canonical reference-simplex P1 barycentric functions satisfy exact partition-of-unity and Kronecker nodal identities.',
            VerificationState.PASS if trusted else VerificationState.FAIL,
            'independent subprocess invocation of the CACE exact-rational affine proof kernel',
            {'checker':a.get('checker'),'checker_version':a.get('checker_version'),'artifact_sha256':a.get('artifact_sha256'),'dimension':a.get('dimension'),
             'claims_checked':a.get('claims_checked'),'returncode':a.get('process_returncode')},
            notes=('Formal evidence is scoped to these affine identities only.','Existing Lean PDE obligations remain separate and unproved.'))]

class FormalTheoremRegistryBridge(Module):
    metadata=ModuleMetadata('formal13.registry_bridge','Machine-Checked Theorem Registry Bridge','0.13.0','Formal Verification',
        'Promote a theorem contract to machine-checked status only when a checker attestation actually passed.',Maturity.BETA)
    inputs=(PortSpec('formal_result','formal_attestation_v13'),)
    outputs=(PortSpec('theorem','theorem_contract_v13'),)
    proof_status=ProofStatus(evidence={EvidenceKind.FORMAL},unit_tests=True,documentation=True)
    def execute(self,inputs,params,ctx):
        r=inputs['formal_result']; art=r['artifact']
        # Do not trust upstream booleans/attestations. Re-check the artifact at the promotion boundary.
        att=invoke_formal_checker(art)
        ok=bool(att.get('passed') and att.get('process_returncode')==0 and att.get('checker')==KERNEL_NAME and att.get('checker_version')==KERNEL_VERSION)
        contract=TheoremContract(theorem_id=art['theorem_id'],statement=art['statement'],
            status=TheoremStatus.MACHINE_CHECKED if ok else TheoremStatus.OBLIGATION,
            assumptions=tuple(['canonical reference simplex',f"dimension={art['dimension']}"]), evidence_kind=EvidenceKind.FORMAL.value if ok else '',
            checker=f'{KERNEL_NAME} {KERNEL_VERSION}' if ok else None, artifact=(f"sha256:{att.get('artifact_sha256','')}" if ok else None))
        d=contract.describe(); d['formal_evidence']=ok; d['attestation_hash']=att.get('artifact_sha256'); d['promotion_recheck']=att
        return {'theorem':d}
    def verify(self,inputs,params,outputs,ctx):
        t=outputs['theorem']; ok=t.get('status')==TheoremStatus.MACHINE_CHECKED.value and t.get('formal_evidence') is True and bool(t.get('checker')) and str(t.get('artifact','')).startswith('sha256:')
        return [VerificationRecord('formal-registry-promotion-v013',EvidenceKind.FORMAL,
            'The theorem registry marks this theorem machine-checked only after successful checker attestation.',
            VerificationState.PASS if ok else VerificationState.FAIL,'attestation-gated theorem-contract construction',t)]

class FormalBridgeSummary(Module):
    metadata=ModuleMetadata('formal13.summary','Formal Verification Bridge Summary','0.13.0','Verification',
        'Summarize machine-checked theorem scope without extending it to unresolved PDE obligations.',Maturity.BETA)
    inputs=(PortSpec('formal_result','formal_attestation_v13'),PortSpec('theorem','theorem_contract_v13'))
    outputs=(PortSpec('summary','formal_summary_v13'),)
    proof_status=ProofStatus(evidence={EvidenceKind.FORMAL},unit_tests=True,documentation=True)
    def execute(self,inputs,params,ctx):
        return {'summary':{'machine_checked':bool(inputs['formal_result']['machine_checked']),'theorem_id':inputs['theorem']['theorem_id'],
            'status':inputs['theorem']['status'],'checker':inputs['theorem']['checker'],'formal_scope':'reference-simplex P1 barycentric affine identities only',
            'pde_reliability_formally_verified':False}}
    def verify(self,inputs,params,outputs,ctx):
        s=outputs['summary']; ok=s['machine_checked'] and s['status']=='machine-checked' and s['pde_reliability_formally_verified'] is False
        return [VerificationRecord('formal-scope-non-escalation-v013',EvidenceKind.FORMAL,
            'Machine-checked affine basis identities are recorded without escalating unresolved PDE reliability obligations.',VerificationState.PASS if ok else VerificationState.FAIL,
            'scope audit',s)]

def register_fem_v013(registry):
    for cls in (ReferenceSimplexFormalProof,FormalTheoremRegistryBridge,FormalBridgeSummary): registry.register(cls)
