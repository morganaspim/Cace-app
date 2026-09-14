from cace_studio.modules.roadmap_v151_200_common import *

class RoadV192(RoadmapStepModule):
    capability_key="192"
    module_id="road192.curl_curl_gradient_nullspace"
    label='Curl-Curl Gradient Nullspace'
    version="1.92.0"
    description='CACE roadmap step: Curl-Curl Gradient Nullspace.'
    evidence_kind=CAP["192"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v2 Roadmap",description,Maturity.EXPERIMENTAL,
        assumptions=("Do not promote reviewed or numerical evidence beyond its declared scope.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Scope-aware evidence only."])

def register_road_v192(registry):
    registry.register(RoadV192)
