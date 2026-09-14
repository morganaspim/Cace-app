from cace_studio.modules.production_v251_300_common import *

class ProductionV284(ProductionStepModule):
    capability_key="284"
    module_id="prod284.maxwell_spurious_mode_audit"
    label='Maxwell Spurious-Mode Audit'
    version="2.84.0"
    description='CACE production release: Maxwell Spurious-Mode Audit.'
    evidence_kind=CAP["284"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v3 Production",description,Maturity.EXPERIMENTAL,
        assumptions=("Preserve theorem/evidence scope and refuse unsupported promotion.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Campaign result scope is explicit in returned artifact."])

def register_production_v284(registry):
    registry.register(ProductionV284)
