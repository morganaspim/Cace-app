from cace_studio.modules.production_v251_300_common import *

class ProductionV294(ProductionStepModule):
    capability_key="294"
    module_id="prod294.sipg_sparse_assembly"
    label='SIPG Sparse Assembly'
    version="2.94.0"
    description='CACE production release: SIPG Sparse Assembly.'
    evidence_kind=CAP["294"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v3 Production",description,Maturity.EXPERIMENTAL,
        assumptions=("Preserve theorem/evidence scope and refuse unsupported promotion.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Campaign result scope is explicit in returned artifact."])

def register_production_v294(registry):
    registry.register(ProductionV294)
