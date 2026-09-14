from cace_studio.modules.production_v251_300_common import *

class ProductionV275(ProductionStepModule):
    capability_key="275"
    module_id="prod275.stokes_pressure_robust_reconstruction"
    label='Stokes Pressure-Robust Reconstruction'
    version="2.75.0"
    description='CACE production release: Stokes Pressure-Robust Reconstruction.'
    evidence_kind=CAP["275"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v3 Production",description,Maturity.EXPERIMENTAL,
        assumptions=("Preserve theorem/evidence scope and refuse unsupported promotion.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Campaign result scope is explicit in returned artifact."])

def register_production_v275(registry):
    registry.register(ProductionV275)
