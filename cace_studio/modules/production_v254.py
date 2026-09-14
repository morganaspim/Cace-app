from cace_studio.modules.production_v251_300_common import *

class ProductionV254(ProductionStepModule):
    capability_key="254"
    module_id="prod254.rt1_sparse_kkt_equilibration"
    label='RT1 Sparse KKT Equilibration'
    version="2.54.0"
    description='CACE production release: RT1 Sparse KKT Equilibration.'
    evidence_kind=CAP["254"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v3 Production",description,Maturity.EXPERIMENTAL,
        assumptions=("Preserve theorem/evidence scope and refuse unsupported promotion.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Campaign result scope is explicit in returned artifact."])

def register_production_v254(registry):
    registry.register(ProductionV254)
