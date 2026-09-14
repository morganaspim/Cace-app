from cace_studio.modules.production_v251_300_common import *

class ProductionV272(ProductionStepModule):
    capability_key="272"
    module_id="prod272.stokes_taylor_hood_topology"
    label='Stokes Taylor-Hood Topology'
    version="2.72.0"
    description='CACE production release: Stokes Taylor-Hood Topology.'
    evidence_kind=CAP["272"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v3 Production",description,Maturity.EXPERIMENTAL,
        assumptions=("Preserve theorem/evidence scope and refuse unsupported promotion.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Campaign result scope is explicit in returned artifact."])

def register_production_v272(registry):
    registry.register(ProductionV272)
