from cace_studio.modules.quality_v131_150_common import *

class QualityV137(QualityStepModule):
    capability_key="137"
    module_id="quality137.guaranteed_d_rfler_marking"
    label='Guaranteed Dörfler Marking'
    version="1.37.0"
    description='CACE development step: Guaranteed Dörfler Marking.'
    evidence_kind=CAP["137"][2]
    metadata=ModuleMetadata(module_id,label,version,"Error Estimation",description,Maturity.EXPERIMENTAL,
        assumptions=("Do not promote diagnostics beyond their declared mathematical scope.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Reviewed mathematics remains distinct from machine-formal evidence."])

def register_quality_v137(registry):
    registry.register(QualityV137)
