from cace_studio.modules.roadmap_v151_200_common import *

class RoadV162(RoadmapStepModule):
    capability_key="162"
    module_id="road162.dwr_localization"
    label='DWR Localization'
    version="1.62.0"
    description='CACE roadmap step: DWR Localization.'
    evidence_kind=CAP["162"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v2 Roadmap",description,Maturity.EXPERIMENTAL,
        assumptions=("Do not promote reviewed or numerical evidence beyond its declared scope.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Scope-aware evidence only."])

def register_road_v162(registry):
    registry.register(RoadV162)
