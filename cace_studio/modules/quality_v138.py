from cace_studio.modules.quality_v131_150_common import *

class QualityV138(QualityStepModule):
    capability_key="138"
    module_id="quality138.adaptive_contraction_audit"
    label='Adaptive Contraction Audit'
    version="1.38.0"
    description='CACE development step: Adaptive Contraction Audit.'
    evidence_kind=CAP["138"][2]
    metadata=ModuleMetadata(module_id,label,version,"Error Estimation",description,Maturity.EXPERIMENTAL,
        assumptions=("Do not promote diagnostics beyond their declared mathematical scope.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Reviewed mathematics remains distinct from machine-formal evidence."])

def register_quality_v138(registry):
    registry.register(QualityV138)
