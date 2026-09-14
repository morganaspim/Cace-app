from cace_studio.modules.roadmap_v151_200_common import *

class RoadV158(RoadmapStepModule):
    capability_key="158"
    module_id="road158.p2_exact_global_solve"
    label='P2 Exact Global Solve'
    version="1.58.0"
    description='CACE roadmap step: P2 Exact Global Solve.'
    evidence_kind=CAP["158"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v2 Roadmap",description,Maturity.EXPERIMENTAL,
        assumptions=("Do not promote reviewed or numerical evidence beyond its declared scope.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Scope-aware evidence only."])

def register_road_v158(registry):
    registry.register(RoadV158)
