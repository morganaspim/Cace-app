from cace_studio.modules.roadmap_v151_200_common import *

class RoadV153(RoadmapStepModule):
    capability_key="153"
    module_id="road153.rt1_affine_divergence"
    label='RT1 Affine Divergence'
    version="1.53.0"
    description='CACE roadmap step: RT1 Affine Divergence.'
    evidence_kind=CAP["153"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v2 Roadmap",description,Maturity.EXPERIMENTAL,
        assumptions=("Do not promote reviewed or numerical evidence beyond its declared scope.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Scope-aware evidence only."])

def register_road_v153(registry):
    registry.register(RoadV153)
