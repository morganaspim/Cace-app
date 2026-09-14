from cace_studio.modules.production_v251_300_common import *

class ProductionV253(ProductionStepModule):
    capability_key="253"
    module_id="prod253.rt1_sparse_assembly"
    label='RT1 Sparse Assembly'
    version="2.53.0"
    description='CACE production release: RT1 Sparse Assembly.'
    evidence_kind=CAP["253"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v3 Production",description,Maturity.EXPERIMENTAL,
        assumptions=("Preserve theorem/evidence scope and refuse unsupported promotion.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Campaign result scope is explicit in returned artifact."])

def register_production_v253(registry):
    registry.register(ProductionV253)
