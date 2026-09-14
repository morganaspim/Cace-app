from cace_studio.modules.production_v251_300_common import *

class ProductionV268(ProductionStepModule):
    capability_key="268"
    module_id="prod268.formal_pde_orthogonality"
    label='Formal PDE Orthogonality'
    version="2.68.0"
    description='CACE production release: Formal PDE Orthogonality.'
    evidence_kind=CAP["268"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v3 Production",description,Maturity.EXPERIMENTAL,
        assumptions=("Preserve theorem/evidence scope and refuse unsupported promotion.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Campaign result scope is explicit in returned artifact."])

def register_production_v268(registry):
    registry.register(ProductionV268)
