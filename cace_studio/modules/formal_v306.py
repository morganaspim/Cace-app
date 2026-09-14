from cace_studio.modules.formal_v301_320_common import *

class FormalV306(FormalStepModule):
    capability_key="306"
    module_id="formal306.admissible_affine_spaces"
    label='Admissible Affine Spaces'
    version="3.06.0"
    description='CACE formalization release: Admissible Affine Spaces.'
    evidence_kind=CAP["306"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE Formal",description,Maturity.EXPERIMENTAL,
        assumptions=("External Lean promotion requires a successful pinned lake build.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Lean NOT_RUN is not formal proof evidence."])

def register_formal_v306(registry):
    registry.register(FormalV306)
