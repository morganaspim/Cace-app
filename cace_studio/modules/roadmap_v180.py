from cace_studio.modules.roadmap_v151_200_common import *

class RoadV180(RoadmapStepModule):
    capability_key="180"
    module_id="road180.mixed_methods_milestone"
    label='Mixed Methods Milestone'
    version="1.80.0"
    description='CACE roadmap step: Mixed Methods Milestone.'
    evidence_kind=CAP["180"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v2 Roadmap",description,Maturity.EXPERIMENTAL,
        assumptions=("Do not promote reviewed or numerical evidence beyond its declared scope.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Scope-aware evidence only."])

def register_road_v180(registry):
    registry.register(RoadV180)
