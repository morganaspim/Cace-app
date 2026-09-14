from cace_studio.modules.production_v251_300_common import *

class ProductionV260(ProductionStepModule):
    capability_key="260"
    module_id="prod260.3d_sparse_equilibrium_assembly"
    label='3D Sparse Equilibrium Assembly'
    version="2.60.0"
    description='CACE production release: 3D Sparse Equilibrium Assembly.'
    evidence_kind=CAP["260"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v3 Production",description,Maturity.EXPERIMENTAL,
        assumptions=("Preserve theorem/evidence scope and refuse unsupported promotion.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Campaign result scope is explicit in returned artifact."])

def register_production_v260(registry):
    registry.register(ProductionV260)
