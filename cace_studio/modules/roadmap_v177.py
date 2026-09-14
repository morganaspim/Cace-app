from cace_studio.modules.roadmap_v151_200_common import *

class RoadV177(RoadmapStepModule):
    capability_key="177"
    module_id="road177.schur_complement_audit"
    label='Schur Complement Audit'
    version="1.77.0"
    description='CACE roadmap step: Schur Complement Audit.'
    evidence_kind=CAP["177"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v2 Roadmap",description,Maturity.EXPERIMENTAL,
        assumptions=("Do not promote reviewed or numerical evidence beyond its declared scope.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Scope-aware evidence only."])

def register_road_v177(registry):
    registry.register(RoadV177)
