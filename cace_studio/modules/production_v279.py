from cace_studio.modules.production_v251_300_common import *

class ProductionV279(ProductionStepModule):
    capability_key="279"
    module_id="prod279.nedelec_reference_element"
    label='Nedelec Reference Element'
    version="2.79.0"
    description='CACE production release: Nedelec Reference Element.'
    evidence_kind=CAP["279"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v3 Production",description,Maturity.EXPERIMENTAL,
        assumptions=("Preserve theorem/evidence scope and refuse unsupported promotion.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Campaign result scope is explicit in returned artifact."])

def register_production_v279(registry):
    registry.register(ProductionV279)
