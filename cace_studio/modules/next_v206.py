from cace_studio.modules.next_v201_225_common import *

class NextV206(NextStepModule):
    capability_key="206"
    module_id="next206.nedelec_reference_unisolvence"
    label='Nedelec Reference Unisolvence'
    version="2.06.0"
    description='CACE next-step release: Nedelec Reference Unisolvence.'
    evidence_kind=CAP["206"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v2.x",description,Maturity.EXPERIMENTAL,
        assumptions=("Preserve evidence and theorem scope.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["No silent promotion of reviewed/numerical evidence."])

def register_next_v206(registry):
    registry.register(NextV206)
