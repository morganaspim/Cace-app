from cace_studio.modules.roadmap_v151_200_common import *

class RoadV178(RoadmapStepModule):
    capability_key="178"
    module_id="road178.brezzi_inf_sup_contract"
    label='Brezzi Inf-Sup Contract'
    version="1.78.0"
    description='CACE roadmap step: Brezzi Inf-Sup Contract.'
    evidence_kind=CAP["178"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v2 Roadmap",description,Maturity.EXPERIMENTAL,
        assumptions=("Do not promote reviewed or numerical evidence beyond its declared scope.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Scope-aware evidence only."])

def register_road_v178(registry):
    registry.register(RoadV178)
