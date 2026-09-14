from cace_studio.modules.production_v251_300_common import *

class ProductionV273(ProductionStepModule):
    capability_key="273"
    module_id="prod273.stokes_sparse_saddle_assembly"
    label='Stokes Sparse Saddle Assembly'
    version="2.73.0"
    description='CACE production release: Stokes Sparse Saddle Assembly.'
    evidence_kind=CAP["273"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v3 Production",description,Maturity.EXPERIMENTAL,
        assumptions=("Preserve theorem/evidence scope and refuse unsupported promotion.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Campaign result scope is explicit in returned artifact."])

def register_production_v273(registry):
    registry.register(ProductionV273)
