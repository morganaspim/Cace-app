from cace_studio.modules.next_v201_225_common import *

class NextV221(NextStepModule):
    capability_key="221"
    module_id="next221.multigrid_two_grid_fixture"
    label='Multigrid Two-Grid Fixture'
    version="2.21.0"
    description='CACE next-step release: Multigrid Two-Grid Fixture.'
    evidence_kind=CAP["221"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v2.x",description,Maturity.EXPERIMENTAL,
        assumptions=("Preserve evidence and theorem scope.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["No silent promotion of reviewed/numerical evidence."])

def register_next_v221(registry):
    registry.register(NextV221)
