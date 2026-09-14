from cace_studio.modules.production_v251_300_common import *

class ProductionV274(ProductionStepModule):
    capability_key="274"
    module_id="prod274.stokes_inf_sup_family_audit"
    label='Stokes Inf-Sup Family Audit'
    version="2.74.0"
    description='CACE production release: Stokes Inf-Sup Family Audit.'
    evidence_kind=CAP["274"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v3 Production",description,Maturity.EXPERIMENTAL,
        assumptions=("Preserve theorem/evidence scope and refuse unsupported promotion.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Campaign result scope is explicit in returned artifact."])

def register_production_v274(registry):
    registry.register(ProductionV274)
