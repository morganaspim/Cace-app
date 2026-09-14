from cace_studio.modules.production_v251_300_common import *

class ProductionV270(ProductionStepModule):
    capability_key="270"
    module_id="prod270.lean_prager_synge_export"
    label='Lean Prager-Synge Export'
    version="2.70.0"
    description='CACE production release: Lean Prager-Synge Export.'
    evidence_kind=CAP["270"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v3 Production",description,Maturity.EXPERIMENTAL,
        assumptions=("Preserve theorem/evidence scope and refuse unsupported promotion.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Campaign result scope is explicit in returned artifact."])

def register_production_v270(registry):
    registry.register(ProductionV270)
