from cace_studio.modules.production_v251_300_common import *

class ProductionV292(ProductionStepModule):
    capability_key="292"
    module_id="prod292.verified_eigensolver_campaign"
    label='Verified Eigensolver Campaign'
    version="2.92.0"
    description='CACE production release: Verified Eigensolver Campaign.'
    evidence_kind=CAP["292"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v3 Production",description,Maturity.EXPERIMENTAL,
        assumptions=("Preserve theorem/evidence scope and refuse unsupported promotion.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Campaign result scope is explicit in returned artifact."])

def register_production_v292(registry):
    registry.register(ProductionV292)
