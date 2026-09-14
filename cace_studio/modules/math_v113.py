from cace_studio.modules.math_v102_125_common import *

class MathV113(MathStepModule):
    capability_key="113"
    module_id="math113.axioms_of_adaptivity"
    label='Axioms of Adaptivity'
    version="1.13.0"
    description='CACE mathematical foundation step: Axioms of Adaptivity.'
    evidence_kind=CAP["113"][2]
    metadata=ModuleMetadata(module_id,label,version,"Mathematical Foundations",description,Maturity.EXPERIMENTAL,
        assumptions=("Imported theorem contracts are reviewed mathematics, not machine-formal proofs.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Scope and hypotheses are enforced per capability."])

def register_math_v113(registry):
    registry.register(MathV113)
