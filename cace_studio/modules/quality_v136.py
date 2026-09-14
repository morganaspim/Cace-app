from cace_studio.modules.quality_v131_150_common import *

class QualityV136(QualityStepModule):
    capability_key="136"
    module_id="quality136.guaranteed_adaptive_stop"
    label='Guaranteed Adaptive Stop'
    version="1.36.0"
    description='CACE development step: Guaranteed Adaptive Stop.'
    evidence_kind=CAP["136"][2]
    metadata=ModuleMetadata(module_id,label,version,"Error Estimation",description,Maturity.EXPERIMENTAL,
        assumptions=("Do not promote diagnostics beyond their declared mathematical scope.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Reviewed mathematics remains distinct from machine-formal evidence."])

def register_quality_v136(registry):
    registry.register(QualityV136)
