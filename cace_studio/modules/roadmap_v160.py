from cace_studio.modules.roadmap_v151_200_common import *

class RoadV160(RoadmapStepModule):
    capability_key="160"
    module_id="road160.p2_production_milestone"
    label='P2 Production Milestone'
    version="1.60.0"
    description='CACE roadmap step: P2 Production Milestone.'
    evidence_kind=CAP["160"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v2 Roadmap",description,Maturity.EXPERIMENTAL,
        assumptions=("Do not promote reviewed or numerical evidence beyond its declared scope.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Scope-aware evidence only."])

def register_road_v160(registry):
    registry.register(RoadV160)
