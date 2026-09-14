from cace_studio.modules.formal_v301_320_common import *

class FormalV312(FormalStepModule):
    capability_key="312"
    module_id="formal312.piola_flux_preservation"
    label='Piola Flux Preservation'
    version="3.12.0"
    description='CACE formalization release: Piola Flux Preservation.'
    evidence_kind=CAP["312"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE Formal",description,Maturity.EXPERIMENTAL,
        assumptions=("External Lean promotion requires a successful pinned lake build.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Lean NOT_RUN is not formal proof evidence."])

def register_formal_v312(registry):
    registry.register(FormalV312)
