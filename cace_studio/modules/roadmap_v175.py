from cace_studio.modules.roadmap_v151_200_common import *

class RoadV175(RoadmapStepModule):
    capability_key="175"
    module_id="road175.adaptivity_theorem_milestone"
    label='Adaptivity Theorem Milestone'
    version="1.75.0"
    description='CACE roadmap step: Adaptivity Theorem Milestone.'
    evidence_kind=CAP["175"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v2 Roadmap",description,Maturity.EXPERIMENTAL,
        assumptions=("Do not promote reviewed or numerical evidence beyond its declared scope.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Scope-aware evidence only."])

def register_road_v175(registry):
    registry.register(RoadV175)
