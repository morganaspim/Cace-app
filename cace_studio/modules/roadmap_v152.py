from cace_studio.modules.roadmap_v151_200_common import *

class RoadV152(RoadmapStepModule):
    capability_key="152"
    module_id="road152.rt1_edge_orientation"
    label='RT1 Edge Orientation'
    version="1.52.0"
    description='CACE roadmap step: RT1 Edge Orientation.'
    evidence_kind=CAP["152"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v2 Roadmap",description,Maturity.EXPERIMENTAL,
        assumptions=("Do not promote reviewed or numerical evidence beyond its declared scope.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Scope-aware evidence only."])

def register_road_v152(registry):
    registry.register(RoadV152)
