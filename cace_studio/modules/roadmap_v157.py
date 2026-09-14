from cace_studio.modules.roadmap_v151_200_common import *

class RoadV157(RoadmapStepModule):
    capability_key="157"
    module_id="road157.p2_global_assembly"
    label='P2 Global Assembly'
    version="1.57.0"
    description='CACE roadmap step: P2 Global Assembly.'
    evidence_kind=CAP["157"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v2 Roadmap",description,Maturity.EXPERIMENTAL,
        assumptions=("Do not promote reviewed or numerical evidence beyond its declared scope.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Scope-aware evidence only."])

def register_road_v157(registry):
    registry.register(RoadV157)
