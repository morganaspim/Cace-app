from cace_studio.modules.roadmap_v151_200_common import *

class RoadV196(RoadmapStepModule):
    capability_key="196"
    module_id="road196.capability_dependency_graph"
    label='Capability Dependency Graph'
    version="1.96.0"
    description='CACE roadmap step: Capability Dependency Graph.'
    evidence_kind=CAP["196"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v2 Roadmap",description,Maturity.EXPERIMENTAL,
        assumptions=("Do not promote reviewed or numerical evidence beyond its declared scope.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Scope-aware evidence only."])

def register_road_v196(registry):
    registry.register(RoadV196)
