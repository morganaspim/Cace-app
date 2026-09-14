from cace_studio.modules.quality_v131_150_common import *

class QualityV149(QualityStepModule):
    capability_key="149"
    module_id="quality149.goal_oriented_marking"
    label='Goal-Oriented Marking'
    version="1.49.0"
    description='CACE development step: Goal-Oriented Marking.'
    evidence_kind=CAP["149"][2]
    metadata=ModuleMetadata(module_id,label,version,"Error Estimation",description,Maturity.EXPERIMENTAL,
        assumptions=("Do not promote diagnostics beyond their declared mathematical scope.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Reviewed mathematics remains distinct from machine-formal evidence."])

def register_quality_v149(registry):
    registry.register(QualityV149)
