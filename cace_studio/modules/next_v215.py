from cace_studio.modules.next_v201_225_common import *

class NextV215(NextStepModule):
    capability_key="215"
    module_id="next215.3d_tetrahedral_p1_geometry"
    label='3D Tetrahedral P1 Geometry'
    version="2.15.0"
    description='CACE next-step release: 3D Tetrahedral P1 Geometry.'
    evidence_kind=CAP["215"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v2.x",description,Maturity.EXPERIMENTAL,
        assumptions=("Preserve evidence and theorem scope.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["No silent promotion of reviewed/numerical evidence."])

def register_next_v215(registry):
    registry.register(NextV215)
