from cace_studio.modules.formal_v301_320_common import *

class FormalV307(FormalStepModule):
    capability_key="307"
    module_id="formal307.weak_green_on_simplices"
    label='Weak Green on Simplices'
    version="3.07.0"
    description='CACE formalization release: Weak Green on Simplices.'
    evidence_kind=CAP["307"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE Formal",description,Maturity.EXPERIMENTAL,
        assumptions=("External Lean promotion requires a successful pinned lake build.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Lean NOT_RUN is not formal proof evidence."])

def register_formal_v307(registry):
    registry.register(FormalV307)
