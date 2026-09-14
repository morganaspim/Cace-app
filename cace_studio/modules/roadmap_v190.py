from cace_studio.modules.roadmap_v151_200_common import *

class RoadV190(RoadmapStepModule):
    capability_key="190"
    module_id="road190.parabolic_milestone"
    label='Parabolic Milestone'
    version="1.90.0"
    description='CACE roadmap step: Parabolic Milestone.'
    evidence_kind=CAP["190"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v2 Roadmap",description,Maturity.EXPERIMENTAL,
        assumptions=("Do not promote reviewed or numerical evidence beyond its declared scope.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Scope-aware evidence only."])

def register_road_v190(registry):
    registry.register(RoadV190)
