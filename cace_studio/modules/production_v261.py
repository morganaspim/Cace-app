from cace_studio.modules.production_v251_300_common import *

class ProductionV261(ProductionStepModule):
    capability_key="261"
    module_id="prod261.3d_patchwise_equilibration"
    label='3D Patchwise Equilibration'
    version="2.61.0"
    description='CACE production release: 3D Patchwise Equilibration.'
    evidence_kind=CAP["261"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v3 Production",description,Maturity.EXPERIMENTAL,
        assumptions=("Preserve theorem/evidence scope and refuse unsupported promotion.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Campaign result scope is explicit in returned artifact."])

def register_production_v261(registry):
    registry.register(ProductionV261)
