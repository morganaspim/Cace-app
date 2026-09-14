from cace_studio.modules.production_v251_300_common import *

class ProductionV263(ProductionStepModule):
    capability_key="263"
    module_id="prod263.3d_source_projection_and_oscillation"
    label='3D Source Projection and Oscillation'
    version="2.63.0"
    description='CACE production release: 3D Source Projection and Oscillation.'
    evidence_kind=CAP["263"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v3 Production",description,Maturity.EXPERIMENTAL,
        assumptions=("Preserve theorem/evidence scope and refuse unsupported promotion.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Campaign result scope is explicit in returned artifact."])

def register_production_v263(registry):
    registry.register(ProductionV263)
