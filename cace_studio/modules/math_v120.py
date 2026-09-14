from cace_studio.modules.math_v102_125_common import *

class MathV120(MathStepModule):
    capability_key="120"
    module_id="math120.feec_de_rham_contract"
    label='FEEC de Rham Contract'
    version="1.20.0"
    description='CACE mathematical foundation step: FEEC de Rham Contract.'
    evidence_kind=CAP["120"][2]
    metadata=ModuleMetadata(module_id,label,version,"Mathematical Foundations",description,Maturity.EXPERIMENTAL,
        assumptions=("Imported theorem contracts are reviewed mathematics, not machine-formal proofs.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Scope and hypotheses are enforced per capability."])

def register_math_v120(registry):
    registry.register(MathV120)
