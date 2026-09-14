from cace_studio.modules.roadmap_v151_200_common import *

class RoadV167(RoadmapStepModule):
    capability_key="167"
    module_id="road167.projected_data_oscillation_bound"
    label='Projected Data Oscillation Bound'
    version="1.67.0"
    description='CACE roadmap step: Projected Data Oscillation Bound.'
    evidence_kind=CAP["167"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v2 Roadmap",description,Maturity.EXPERIMENTAL,
        assumptions=("Do not promote reviewed or numerical evidence beyond its declared scope.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Scope-aware evidence only."])

def register_road_v167(registry):
    registry.register(RoadV167)
