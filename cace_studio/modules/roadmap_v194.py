from cace_studio.modules.roadmap_v151_200_common import *

class RoadV194(RoadmapStepModule):
    capability_key="194"
    module_id="road194.feec_contract"
    label='FEEC Contract'
    version="1.94.0"
    description='CACE roadmap step: FEEC Contract.'
    evidence_kind=CAP["194"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v2 Roadmap",description,Maturity.EXPERIMENTAL,
        assumptions=("Do not promote reviewed or numerical evidence beyond its declared scope.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Scope-aware evidence only."])

def register_road_v194(registry):
    registry.register(RoadV194)
