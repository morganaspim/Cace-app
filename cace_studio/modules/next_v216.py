from cace_studio.modules.next_v201_225_common import *

class NextV216(NextStepModule):
    capability_key="216"
    module_id="next216.3d_tetrahedral_rt0_fixture"
    label='3D Tetrahedral RT0 Fixture'
    version="2.16.0"
    description='CACE next-step release: 3D Tetrahedral RT0 Fixture.'
    evidence_kind=CAP["216"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v2.x",description,Maturity.EXPERIMENTAL,
        assumptions=("Preserve evidence and theorem scope.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["No silent promotion of reviewed/numerical evidence."])

def register_next_v216(registry):
    registry.register(NextV216)
