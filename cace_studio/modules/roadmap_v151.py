from cace_studio.modules.roadmap_v151_200_common import *

class RoadV151(RoadmapStepModule):
    capability_key="151"
    module_id="road151.rt1_unisolvence"
    label='RT1 Unisolvence'
    version="1.51.0"
    description='CACE roadmap step: RT1 Unisolvence.'
    evidence_kind=CAP["151"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v2 Roadmap",description,Maturity.EXPERIMENTAL,
        assumptions=("Do not promote reviewed or numerical evidence beyond its declared scope.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Scope-aware evidence only."])

def register_road_v151(registry):
    registry.register(RoadV151)
