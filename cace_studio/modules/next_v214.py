from cace_studio.modules.next_v201_225_common import *

class NextV214(NextStepModule):
    capability_key="214"
    module_id="next214.hp_adaptivity_decision"
    label='hp Adaptivity Decision'
    version="2.14.0"
    description='CACE next-step release: hp Adaptivity Decision.'
    evidence_kind=CAP["214"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v2.x",description,Maturity.EXPERIMENTAL,
        assumptions=("Preserve evidence and theorem scope.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["No silent promotion of reviewed/numerical evidence."])

def register_next_v214(registry):
    registry.register(NextV214)
