from cace_studio.modules.roadmap_v151_200_common import *

class RoadV197(RoadmapStepModule):
    capability_key="197"
    module_id="road197.evidence_scope_audit"
    label='Evidence Scope Audit'
    version="1.97.0"
    description='CACE roadmap step: Evidence Scope Audit.'
    evidence_kind=CAP["197"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v2 Roadmap",description,Maturity.EXPERIMENTAL,
        assumptions=("Do not promote reviewed or numerical evidence beyond its declared scope.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Scope-aware evidence only."])

def register_road_v197(registry):
    registry.register(RoadV197)
