from cace_studio.modules.production_v251_300_common import *

class ProductionV300(ProductionStepModule):
    capability_key="300"
    module_id="prod300.cace_v3_0_production_milestone"
    label='CACE v3.0 Production Milestone'
    version="3.0.0"
    description='CACE production release: CACE v3.0 Production Milestone.'
    evidence_kind=CAP["300"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v3 Production",description,Maturity.EXPERIMENTAL,
        assumptions=("Preserve theorem/evidence scope and refuse unsupported promotion.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Campaign result scope is explicit in returned artifact."])

def register_production_v300(registry):
    registry.register(ProductionV300)
