from cace_studio.modules.roadmap_v151_200_common import *

class RoadV172(RoadmapStepModule):
    capability_key="172"
    module_id="road172.estimator_reduction_audit"
    label='Estimator Reduction Audit'
    version="1.72.0"
    description='CACE roadmap step: Estimator Reduction Audit.'
    evidence_kind=CAP["172"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v2 Roadmap",description,Maturity.EXPERIMENTAL,
        assumptions=("Do not promote reviewed or numerical evidence beyond its declared scope.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Scope-aware evidence only."])

def register_road_v172(registry):
    registry.register(RoadV172)
