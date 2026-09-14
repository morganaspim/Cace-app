from cace_studio.modules.next_v201_225_common import *

class NextV213(NextStepModule):
    capability_key="213"
    module_id="next213.space_time_adaptive_certification"
    label='Space-Time Adaptive Certification'
    version="2.13.0"
    description='CACE next-step release: Space-Time Adaptive Certification.'
    evidence_kind=CAP["213"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v2.x",description,Maturity.EXPERIMENTAL,
        assumptions=("Preserve evidence and theorem scope.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["No silent promotion of reviewed/numerical evidence."])

def register_next_v213(registry):
    registry.register(NextV213)
