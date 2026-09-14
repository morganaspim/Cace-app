from cace_studio.modules.next_v201_225_common import *

class NextV224(NextStepModule):
    capability_key="224"
    module_id="next224.certified_reduced_basis_bound"
    label='Certified Reduced-Basis Bound'
    version="2.24.0"
    description='CACE next-step release: Certified Reduced-Basis Bound.'
    evidence_kind=CAP["224"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v2.x",description,Maturity.EXPERIMENTAL,
        assumptions=("Preserve evidence and theorem scope.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["No silent promotion of reviewed/numerical evidence."])

def register_next_v224(registry):
    registry.register(NextV224)
