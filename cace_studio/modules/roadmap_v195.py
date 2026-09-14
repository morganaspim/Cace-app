from cace_studio.modules.roadmap_v151_200_common import *

class RoadV195(RoadmapStepModule):
    capability_key="195"
    module_id="road195.maxwell_milestone"
    label='Maxwell Milestone'
    version="1.95.0"
    description='CACE roadmap step: Maxwell Milestone.'
    evidence_kind=CAP["195"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v2 Roadmap",description,Maturity.EXPERIMENTAL,
        assumptions=("Do not promote reviewed or numerical evidence beyond its declared scope.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Scope-aware evidence only."])

def register_road_v195(registry):
    registry.register(RoadV195)
