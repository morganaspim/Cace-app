from cace_studio.modules.production_v251_300_common import *

class ProductionV283(ProductionStepModule):
    capability_key="283"
    module_id="prod283.maxwell_boundary_and_gauge"
    label='Maxwell Boundary and Gauge'
    version="2.83.0"
    description='CACE production release: Maxwell Boundary and Gauge.'
    evidence_kind=CAP["283"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v3 Production",description,Maturity.EXPERIMENTAL,
        assumptions=("Preserve theorem/evidence scope and refuse unsupported promotion.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Campaign result scope is explicit in returned artifact."])

def register_production_v283(registry):
    registry.register(ProductionV283)
