from cace_studio.modules.roadmap_v151_200_common import *

class RoadV198(RoadmapStepModule):
    capability_key="198"
    module_id="road198.reproducibility_capsule_v2"
    label='Reproducibility Capsule v2'
    version="1.98.0"
    description='CACE roadmap step: Reproducibility Capsule v2.'
    evidence_kind=CAP["198"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v2 Roadmap",description,Maturity.EXPERIMENTAL,
        assumptions=("Do not promote reviewed or numerical evidence beyond its declared scope.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Scope-aware evidence only."])

def register_road_v198(registry):
    registry.register(RoadV198)
