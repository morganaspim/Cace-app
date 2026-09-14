from cace_studio.modules.production_v251_300_common import *

class ProductionV299(ProductionStepModule):
    capability_key="299"
    module_id="prod299.helmholtz_block_real_solver"
    label='Helmholtz Block-Real Solver'
    version="2.99.0"
    description='CACE production release: Helmholtz Block-Real Solver.'
    evidence_kind=CAP["299"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v3 Production",description,Maturity.EXPERIMENTAL,
        assumptions=("Preserve theorem/evidence scope and refuse unsupported promotion.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Campaign result scope is explicit in returned artifact."])

def register_production_v299(registry):
    registry.register(ProductionV299)
