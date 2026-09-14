from cace_studio.modules.production_v251_300_common import *

class ProductionV262(ProductionStepModule):
    capability_key="262"
    module_id="prod262.3d_spd_constitutive_minimization"
    label='3D SPD Constitutive Minimization'
    version="2.62.0"
    description='CACE production release: 3D SPD Constitutive Minimization.'
    evidence_kind=CAP["262"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v3 Production",description,Maturity.EXPERIMENTAL,
        assumptions=("Preserve theorem/evidence scope and refuse unsupported promotion.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Campaign result scope is explicit in returned artifact."])

def register_production_v262(registry):
    registry.register(ProductionV262)
