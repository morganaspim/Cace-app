from cace_studio.modules.roadmap_v151_200_common import *

class RoadV163(RoadmapStepModule):
    capability_key="163"
    module_id="road163.dwr_goal_marking"
    label='DWR Goal Marking'
    version="1.63.0"
    description='CACE roadmap step: DWR Goal Marking.'
    evidence_kind=CAP["163"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v2 Roadmap",description,Maturity.EXPERIMENTAL,
        assumptions=("Do not promote reviewed or numerical evidence beyond its declared scope.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Scope-aware evidence only."])

def register_road_v163(registry):
    registry.register(RoadV163)
