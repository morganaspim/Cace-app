from cace_studio.modules.next_v201_225_common import *

class NextV225(NextStepModule):
    capability_key="225"
    module_id="next225.cace_v2_25_milestone"
    label='CACE v2.25 Milestone'
    version="2.25.0"
    description='CACE next-step release: CACE v2.25 Milestone.'
    evidence_kind=CAP["225"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v2.x",description,Maturity.EXPERIMENTAL,
        assumptions=("Preserve evidence and theorem scope.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["No silent promotion of reviewed/numerical evidence."])

def register_next_v225(registry):
    registry.register(NextV225)
