from cace_studio.modules.roadmap_v151_200_common import *

class RoadV176(RoadmapStepModule):
    capability_key="176"
    module_id="road176.mixed_saddle_fixture"
    label='Mixed Saddle Fixture'
    version="1.76.0"
    description='CACE roadmap step: Mixed Saddle Fixture.'
    evidence_kind=CAP["176"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v2 Roadmap",description,Maturity.EXPERIMENTAL,
        assumptions=("Do not promote reviewed or numerical evidence beyond its declared scope.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Scope-aware evidence only."])

def register_road_v176(registry):
    registry.register(RoadV176)
