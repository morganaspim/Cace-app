from cace_studio.modules.next_v201_225_common import *

class NextV218(NextStepModule):
    capability_key="218"
    module_id="next218.stokes_mixed_block_fixture"
    label='Stokes Mixed Block Fixture'
    version="2.18.0"
    description='CACE next-step release: Stokes Mixed Block Fixture.'
    evidence_kind=CAP["218"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v2.x",description,Maturity.EXPERIMENTAL,
        assumptions=("Preserve evidence and theorem scope.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["No silent promotion of reviewed/numerical evidence."])

def register_next_v218(registry):
    registry.register(NextV218)
