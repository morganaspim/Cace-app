from cace_studio.modules.roadmap_v151_200_common import *

class RoadV193(RoadmapStepModule):
    capability_key="193"
    module_id="road193.gauge_fixed_maxwell_fixture"
    label='Gauge-Fixed Maxwell Fixture'
    version="1.93.0"
    description='CACE roadmap step: Gauge-Fixed Maxwell Fixture.'
    evidence_kind=CAP["193"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v2 Roadmap",description,Maturity.EXPERIMENTAL,
        assumptions=("Do not promote reviewed or numerical evidence beyond its declared scope.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Scope-aware evidence only."])

def register_road_v193(registry):
    registry.register(RoadV193)
