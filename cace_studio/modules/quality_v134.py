from cace_studio.modules.quality_v131_150_common import *

class QualityV134(QualityStepModule):
    capability_key="134"
    module_id="quality134.variable_spd_and_projected_source_flux"
    label='Variable-SPD and Projected-Source Flux'
    version="1.34.0"
    description='CACE development step: Variable-SPD and Projected-Source Flux.'
    evidence_kind=CAP["134"][2]
    metadata=ModuleMetadata(module_id,label,version,"Error Estimation",description,Maturity.EXPERIMENTAL,
        assumptions=("Do not promote diagnostics beyond their declared mathematical scope.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Reviewed mathematics remains distinct from machine-formal evidence."])

def register_quality_v134(registry):
    registry.register(QualityV134)
