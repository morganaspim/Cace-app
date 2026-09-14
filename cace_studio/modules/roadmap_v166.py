from cace_studio.modules.roadmap_v151_200_common import *

class RoadV166(RoadmapStepModule):
    capability_key="166"
    module_id="road166.coefficient_contrast_audit"
    label='Coefficient Contrast Audit'
    version="1.66.0"
    description='CACE roadmap step: Coefficient Contrast Audit.'
    evidence_kind=CAP["166"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v2 Roadmap",description,Maturity.EXPERIMENTAL,
        assumptions=("Do not promote reviewed or numerical evidence beyond its declared scope.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Scope-aware evidence only."])

def register_road_v166(registry):
    registry.register(RoadV166)
