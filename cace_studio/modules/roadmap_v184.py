from cace_studio.modules.roadmap_v151_200_common import *

class RoadV184(RoadmapStepModule):
    capability_key="184"
    module_id="road184.min_max_contract"
    label='Min-Max Contract'
    version="1.84.0"
    description='CACE roadmap step: Min-Max Contract.'
    evidence_kind=CAP["184"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v2 Roadmap",description,Maturity.EXPERIMENTAL,
        assumptions=("Do not promote reviewed or numerical evidence beyond its declared scope.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Scope-aware evidence only."])

def register_road_v184(registry):
    registry.register(RoadV184)
