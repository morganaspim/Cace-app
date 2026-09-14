from cace_studio.modules.production_v251_300_common import *

class ProductionV257(ProductionStepModule):
    capability_key="257"
    module_id="prod257.rt1_production_campaign"
    label='RT1 Production Campaign'
    version="2.57.0"
    description='CACE production release: RT1 Production Campaign.'
    evidence_kind=CAP["257"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v3 Production",description,Maturity.EXPERIMENTAL,
        assumptions=("Preserve theorem/evidence scope and refuse unsupported promotion.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Campaign result scope is explicit in returned artifact."])

def register_production_v257(registry):
    registry.register(ProductionV257)
