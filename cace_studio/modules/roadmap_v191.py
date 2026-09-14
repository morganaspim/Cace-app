from cace_studio.modules.roadmap_v151_200_common import *

class RoadV191(RoadmapStepModule):
    capability_key="191"
    module_id="road191.discrete_de_rham_complex"
    label='Discrete de Rham Complex'
    version="1.91.0"
    description='CACE roadmap step: Discrete de Rham Complex.'
    evidence_kind=CAP["191"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v2 Roadmap",description,Maturity.EXPERIMENTAL,
        assumptions=("Do not promote reviewed or numerical evidence beyond its declared scope.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Scope-aware evidence only."])

def register_road_v191(registry):
    registry.register(RoadV191)
