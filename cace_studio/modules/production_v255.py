from cace_studio.modules.production_v251_300_common import *

class ProductionV255(ProductionStepModule):
    capability_key="255"
    module_id="prod255.rt1_static_condensation"
    label='RT1 Static Condensation'
    version="2.55.0"
    description='CACE production release: RT1 Static Condensation.'
    evidence_kind=CAP["255"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v3 Production",description,Maturity.EXPERIMENTAL,
        assumptions=("Preserve theorem/evidence scope and refuse unsupported promotion.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Campaign result scope is explicit in returned artifact."])

def register_production_v255(registry):
    registry.register(ProductionV255)
