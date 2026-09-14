from cace_studio.modules.roadmap_v151_200_common import *

class RoadV200(RoadmapStepModule):
    capability_key="200"
    module_id="road200.cace_v2_0_milestone"
    label='CACE v2.0 Milestone'
    version="2.0.0"
    description='CACE roadmap step: CACE v2.0 Milestone.'
    evidence_kind=CAP["200"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v2 Roadmap",description,Maturity.EXPERIMENTAL,
        assumptions=("Do not promote reviewed or numerical evidence beyond its declared scope.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Scope-aware evidence only."])

def register_road_v200(registry):
    registry.register(RoadV200)
