from cace_studio.modules.roadmap_v151_200_common import *

class RoadV155(RoadmapStepModule):
    capability_key="155"
    module_id="road155.rt1_milestone"
    label='RT1 Milestone'
    version="1.55.0"
    description='CACE roadmap step: RT1 Milestone.'
    evidence_kind=CAP["155"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v2 Roadmap",description,Maturity.EXPERIMENTAL,
        assumptions=("Do not promote reviewed or numerical evidence beyond its declared scope.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Scope-aware evidence only."])

def register_road_v155(registry):
    registry.register(RoadV155)
