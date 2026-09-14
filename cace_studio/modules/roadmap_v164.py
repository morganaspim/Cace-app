from cace_studio.modules.roadmap_v151_200_common import *

class RoadV164(RoadmapStepModule):
    capability_key="164"
    module_id="road164.dwr_goal_stop_policy"
    label='DWR Goal Stop Policy'
    version="1.64.0"
    description='CACE roadmap step: DWR Goal Stop Policy.'
    evidence_kind=CAP["164"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v2 Roadmap",description,Maturity.EXPERIMENTAL,
        assumptions=("Do not promote reviewed or numerical evidence beyond its declared scope.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Scope-aware evidence only."])

def register_road_v164(registry):
    registry.register(RoadV164)
