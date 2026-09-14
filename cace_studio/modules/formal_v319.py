from cace_studio.modules.formal_v301_320_common import *

class FormalV319(FormalStepModule):
    capability_key="319"
    module_id="formal319.dual_verifier_certificate_binding"
    label='Dual Verifier Certificate Binding'
    version="3.19.0"
    description='CACE formalization release: Dual Verifier Certificate Binding.'
    evidence_kind=CAP["319"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE Formal",description,Maturity.EXPERIMENTAL,
        assumptions=("External Lean promotion requires a successful pinned lake build.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Lean NOT_RUN is not formal proof evidence."])

def register_formal_v319(registry):
    registry.register(FormalV319)
