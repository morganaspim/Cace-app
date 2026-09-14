from cace_studio.modules.production_v251_300_common import *

class ProductionV278(ProductionStepModule):
    capability_key="278"
    module_id="prod278.stokes_production_campaign"
    label='Stokes Production Campaign'
    version="2.78.0"
    description='CACE production release: Stokes Production Campaign.'
    evidence_kind=CAP["278"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v3 Production",description,Maturity.EXPERIMENTAL,
        assumptions=("Preserve theorem/evidence scope and refuse unsupported promotion.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Campaign result scope is explicit in returned artifact."])

def register_production_v278(registry):
    registry.register(ProductionV278)
