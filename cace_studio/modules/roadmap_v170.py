from cace_studio.modules.roadmap_v151_200_common import *

class RoadV170(RoadmapStepModule):
    capability_key="170"
    module_id="road170.robust_guarantee_milestone"
    label='Robust Guarantee Milestone'
    version="1.70.0"
    description='CACE roadmap step: Robust Guarantee Milestone.'
    evidence_kind=CAP["170"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v2 Roadmap",description,Maturity.EXPERIMENTAL,
        assumptions=("Do not promote reviewed or numerical evidence beyond its declared scope.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Scope-aware evidence only."])

def register_road_v170(registry):
    registry.register(RoadV170)
