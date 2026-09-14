from cace_studio.modules.next_v201_225_common import *

class NextV207(NextStepModule):
    capability_key="207"
    module_id="next207.nedelec_global_orientation"
    label='Nedelec Global Orientation'
    version="2.07.0"
    description='CACE next-step release: Nedelec Global Orientation.'
    evidence_kind=CAP["207"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v2.x",description,Maturity.EXPERIMENTAL,
        assumptions=("Preserve evidence and theorem scope.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["No silent promotion of reviewed/numerical evidence."])

def register_next_v207(registry):
    registry.register(NextV207)
