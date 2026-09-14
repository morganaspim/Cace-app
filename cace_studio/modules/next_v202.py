from cace_studio.modules.next_v201_225_common import *

class NextV202(NextStepModule):
    capability_key="202"
    module_id="next202.global_rt1_orientation"
    label='Global RT1 Orientation'
    version="2.02.0"
    description='CACE next-step release: Global RT1 Orientation.'
    evidence_kind=CAP["202"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v2.x",description,Maturity.EXPERIMENTAL,
        assumptions=("Preserve evidence and theorem scope.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["No silent promotion of reviewed/numerical evidence."])

def register_next_v202(registry):
    registry.register(NextV202)
