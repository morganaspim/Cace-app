from cace_studio.modules.production_v251_300_common import *

class ProductionV256(ProductionStepModule):
    capability_key="256"
    module_id="prod256.rt1_patchwise_reconstruction"
    label='RT1 Patchwise Reconstruction'
    version="2.56.0"
    description='CACE production release: RT1 Patchwise Reconstruction.'
    evidence_kind=CAP["256"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v3 Production",description,Maturity.EXPERIMENTAL,
        assumptions=("Preserve theorem/evidence scope and refuse unsupported promotion.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Campaign result scope is explicit in returned artifact."])

def register_production_v256(registry):
    registry.register(ProductionV256)
