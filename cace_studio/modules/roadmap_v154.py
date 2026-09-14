from cace_studio.modules.roadmap_v151_200_common import *

class RoadV154(RoadmapStepModule):
    capability_key="154"
    module_id="road154.rt1_affine_source_guarantee_bridge"
    label='RT1 Affine-Source Guarantee Bridge'
    version="1.54.0"
    description='CACE roadmap step: RT1 Affine-Source Guarantee Bridge.'
    evidence_kind=CAP["154"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v2 Roadmap",description,Maturity.EXPERIMENTAL,
        assumptions=("Do not promote reviewed or numerical evidence beyond its declared scope.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Scope-aware evidence only."])

def register_road_v154(registry):
    registry.register(RoadV154)
