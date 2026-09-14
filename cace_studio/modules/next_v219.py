from cace_studio.modules.next_v201_225_common import *

class NextV219(NextStepModule):
    capability_key="219"
    module_id="next219.maxwell_nedelec_mass_fixture"
    label='Maxwell Nedelec Mass Fixture'
    version="2.19.0"
    description='CACE next-step release: Maxwell Nedelec Mass Fixture.'
    evidence_kind=CAP["219"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v2.x",description,Maturity.EXPERIMENTAL,
        assumptions=("Preserve evidence and theorem scope.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["No silent promotion of reviewed/numerical evidence."])

def register_next_v219(registry):
    registry.register(NextV219)
