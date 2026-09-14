from cace_studio.modules.roadmap_v151_200_common import *

class RoadV165(RoadmapStepModule):
    capability_key="165"
    module_id="road165.pde_dwr_milestone"
    label='PDE DWR Milestone'
    version="1.65.0"
    description='CACE roadmap step: PDE DWR Milestone.'
    evidence_kind=CAP["165"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v2 Roadmap",description,Maturity.EXPERIMENTAL,
        assumptions=("Do not promote reviewed or numerical evidence beyond its declared scope.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Scope-aware evidence only."])

def register_road_v165(registry):
    registry.register(RoadV165)
