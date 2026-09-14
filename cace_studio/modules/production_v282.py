from cace_studio.modules.production_v251_300_common import *

class ProductionV282(ProductionStepModule):
    capability_key="282"
    module_id="prod282.maxwell_sparse_operator"
    label='Maxwell Sparse Operator'
    version="2.82.0"
    description='CACE production release: Maxwell Sparse Operator.'
    evidence_kind=CAP["282"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v3 Production",description,Maturity.EXPERIMENTAL,
        assumptions=("Preserve theorem/evidence scope and refuse unsupported promotion.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Campaign result scope is explicit in returned artifact."])

def register_production_v282(registry):
    registry.register(ProductionV282)
