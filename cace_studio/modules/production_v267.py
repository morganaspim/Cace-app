from cace_studio.modules.production_v251_300_common import *

class ProductionV267(ProductionStepModule):
    capability_key="267"
    module_id="prod267.formal_weak_green_bridge"
    label='Formal Weak Green Bridge'
    version="2.67.0"
    description='CACE production release: Formal Weak Green Bridge.'
    evidence_kind=CAP["267"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v3 Production",description,Maturity.EXPERIMENTAL,
        assumptions=("Preserve theorem/evidence scope and refuse unsupported promotion.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Campaign result scope is explicit in returned artifact."])

def register_production_v267(registry):
    registry.register(ProductionV267)
