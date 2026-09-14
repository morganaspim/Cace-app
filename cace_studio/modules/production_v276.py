from cace_studio.modules.production_v251_300_common import *

class ProductionV276(ProductionStepModule):
    capability_key="276"
    module_id="prod276.stokes_fortin_audit"
    label='Stokes Fortin Audit'
    version="2.76.0"
    description='CACE production release: Stokes Fortin Audit.'
    evidence_kind=CAP["276"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v3 Production",description,Maturity.EXPERIMENTAL,
        assumptions=("Preserve theorem/evidence scope and refuse unsupported promotion.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Campaign result scope is explicit in returned artifact."])

def register_production_v276(registry):
    registry.register(ProductionV276)
