from cace_studio.modules.roadmap_v151_200_common import *

class RoadV199(RoadmapStepModule):
    capability_key="199"
    module_id="road199.v2_qualification_matrix"
    label='v2 Qualification Matrix'
    version="1.99.0"
    description='CACE roadmap step: v2 Qualification Matrix.'
    evidence_kind=CAP["199"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v2 Roadmap",description,Maturity.EXPERIMENTAL,
        assumptions=("Do not promote reviewed or numerical evidence beyond its declared scope.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Scope-aware evidence only."])

def register_road_v199(registry):
    registry.register(RoadV199)
