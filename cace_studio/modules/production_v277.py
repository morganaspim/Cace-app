from cace_studio.modules.production_v251_300_common import *

class ProductionV277(ProductionStepModule):
    capability_key="277"
    module_id="prod277.stokes_schur_preconditioner"
    label='Stokes Schur Preconditioner'
    version="2.77.0"
    description='CACE production release: Stokes Schur Preconditioner.'
    evidence_kind=CAP["277"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v3 Production",description,Maturity.EXPERIMENTAL,
        assumptions=("Preserve theorem/evidence scope and refuse unsupported promotion.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Campaign result scope is explicit in returned artifact."])

def register_production_v277(registry):
    registry.register(ProductionV277)
