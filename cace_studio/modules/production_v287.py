from cace_studio.modules.production_v251_300_common import *

class ProductionV287(ProductionStepModule):
    capability_key="287"
    module_id="prod287.eigen_sparse_ordering"
    label='Eigen Sparse Ordering'
    version="2.87.0"
    description='CACE production release: Eigen Sparse Ordering.'
    evidence_kind=CAP["287"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v3 Production",description,Maturity.EXPERIMENTAL,
        assumptions=("Preserve theorem/evidence scope and refuse unsupported promotion.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Campaign result scope is explicit in returned artifact."])

def register_production_v287(registry):
    registry.register(ProductionV287)
