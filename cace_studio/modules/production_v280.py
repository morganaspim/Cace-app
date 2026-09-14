from cace_studio.modules.production_v251_300_common import *

class ProductionV280(ProductionStepModule):
    capability_key="280"
    module_id="prod280.nedelec_orientation"
    label='Nedelec Orientation'
    version="2.80.0"
    description='CACE production release: Nedelec Orientation.'
    evidence_kind=CAP["280"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v3 Production",description,Maturity.EXPERIMENTAL,
        assumptions=("Preserve theorem/evidence scope and refuse unsupported promotion.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Campaign result scope is explicit in returned artifact."])

def register_production_v280(registry):
    registry.register(ProductionV280)
