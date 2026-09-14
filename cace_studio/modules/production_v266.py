from cace_studio.modules.production_v251_300_common import *

class ProductionV266(ProductionStepModule):
    capability_key="266"
    module_id="prod266.formal_admissible_spaces"
    label='Formal Admissible Spaces'
    version="2.66.0"
    description='CACE production release: Formal Admissible Spaces.'
    evidence_kind=CAP["266"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v3 Production",description,Maturity.EXPERIMENTAL,
        assumptions=("Preserve theorem/evidence scope and refuse unsupported promotion.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Campaign result scope is explicit in returned artifact."])

def register_production_v266(registry):
    registry.register(ProductionV266)
