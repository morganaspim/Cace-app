from cace_studio.modules.formal_v301_320_common import *

class FormalV318(FormalStepModule):
    capability_key="318"
    module_id="formal318.cross_prover_formalization_specification"
    label='Cross-Prover Formalization Specification'
    version="3.18.0"
    description='CACE formalization release: Cross-Prover Formalization Specification.'
    evidence_kind=CAP["318"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE Formal",description,Maturity.EXPERIMENTAL,
        assumptions=("External Lean promotion requires a successful pinned lake build.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Lean NOT_RUN is not formal proof evidence."])

def register_formal_v318(registry):
    registry.register(FormalV318)
