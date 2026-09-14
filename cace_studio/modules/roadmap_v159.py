from cace_studio.modules.roadmap_v151_200_common import *

class RoadV159(RoadmapStepModule):
    capability_key="159"
    module_id="road159.p2_vs_p1_discrete_comparison"
    label='P2 vs P1 Discrete Comparison'
    version="1.59.0"
    description='CACE roadmap step: P2 vs P1 Discrete Comparison.'
    evidence_kind=CAP["159"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v2 Roadmap",description,Maturity.EXPERIMENTAL,
        assumptions=("Do not promote reviewed or numerical evidence beyond its declared scope.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Scope-aware evidence only."])

def register_road_v159(registry):
    registry.register(RoadV159)
