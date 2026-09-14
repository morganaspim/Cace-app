from cace_studio.modules.production_v251_300_common import *

class ProductionV285(ProductionStepModule):
    capability_key="285"
    module_id="prod285.maxwell_equilibrated_estimator"
    label='Maxwell Equilibrated Estimator'
    version="2.85.0"
    description='CACE production release: Maxwell Equilibrated Estimator.'
    evidence_kind=CAP["285"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v3 Production",description,Maturity.EXPERIMENTAL,
        assumptions=("Preserve theorem/evidence scope and refuse unsupported promotion.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Campaign result scope is explicit in returned artifact."])

def register_production_v285(registry):
    registry.register(ProductionV285)
