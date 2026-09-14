from cace_studio.modules.formal_v301_320_common import *

class FormalV301(FormalStepModule):
    capability_key="301"
    module_id="formal301.pinned_lean_toolchain"
    label='Pinned Lean Toolchain'
    version="3.01.0"
    description='CACE formalization release: Pinned Lean Toolchain.'
    evidence_kind=CAP["301"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE Formal",description,Maturity.EXPERIMENTAL,
        assumptions=("External Lean promotion requires a successful pinned lake build.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Lean NOT_RUN is not formal proof evidence."])

def register_formal_v301(registry):
    registry.register(FormalV301)
