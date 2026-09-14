from cace_studio.modules.quality_v131_150_common import *

class QualityV145(QualityStepModule):
    capability_key="145"
    module_id="quality145.higher_order_flux_boundary"
    label='Higher-Order Flux Boundary'
    version="1.45.0"
    description='CACE development step: Higher-Order Flux Boundary.'
    evidence_kind=CAP["145"][2]
    metadata=ModuleMetadata(module_id,label,version,"Error Estimation",description,Maturity.EXPERIMENTAL,
        assumptions=("Do not promote diagnostics beyond their declared mathematical scope.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Reviewed mathematics remains distinct from machine-formal evidence."])

def register_quality_v145(registry):
    registry.register(QualityV145)
