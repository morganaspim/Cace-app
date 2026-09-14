from cace_studio.modules.quality_v131_150_common import *

class QualityV148(QualityStepModule):
    capability_key="148"
    module_id="quality148.dwr_localization"
    label='DWR Localization'
    version="1.48.0"
    description='CACE development step: DWR Localization.'
    evidence_kind=CAP["148"][2]
    metadata=ModuleMetadata(module_id,label,version,"Error Estimation",description,Maturity.EXPERIMENTAL,
        assumptions=("Do not promote diagnostics beyond their declared mathematical scope.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Reviewed mathematics remains distinct from machine-formal evidence."])

def register_quality_v148(registry):
    registry.register(QualityV148)
