from cace_studio.modules.production_v251_300_common import *

class ProductionV295(ProductionStepModule):
    capability_key="295"
    module_id="prod295.dg_equilibrated_estimator"
    label='DG Equilibrated Estimator'
    version="2.95.0"
    description='CACE production release: DG Equilibrated Estimator.'
    evidence_kind=CAP["295"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v3 Production",description,Maturity.EXPERIMENTAL,
        assumptions=("Preserve theorem/evidence scope and refuse unsupported promotion.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Campaign result scope is explicit in returned artifact."])

def register_production_v295(registry):
    registry.register(ProductionV295)
