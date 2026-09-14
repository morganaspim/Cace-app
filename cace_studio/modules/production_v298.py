from cace_studio.modules.production_v251_300_common import *

class ProductionV298(ProductionStepModule):
    capability_key="298"
    module_id="prod298.contact_active_set_solver"
    label='Contact Active-Set Solver'
    version="2.98.0"
    description='CACE production release: Contact Active-Set Solver.'
    evidence_kind=CAP["298"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v3 Production",description,Maturity.EXPERIMENTAL,
        assumptions=("Preserve theorem/evidence scope and refuse unsupported promotion.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Campaign result scope is explicit in returned artifact."])

def register_production_v298(registry):
    registry.register(ProductionV298)
