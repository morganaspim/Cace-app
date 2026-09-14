from cace_studio.modules.production_v251_300_common import *

class ProductionV296(ProductionStepModule):
    capability_key="296"
    module_id="prod296.supg_sparse_assembly"
    label='SUPG Sparse Assembly'
    version="2.96.0"
    description='CACE production release: SUPG Sparse Assembly.'
    evidence_kind=CAP["296"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v3 Production",description,Maturity.EXPERIMENTAL,
        assumptions=("Preserve theorem/evidence scope and refuse unsupported promotion.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Campaign result scope is explicit in returned artifact."])

def register_production_v296(registry):
    registry.register(ProductionV296)
