from cace_studio.modules.production_v251_300_common import *

class ProductionV289(ProductionStepModule):
    capability_key="289"
    module_id="prod289.spectral_initial_brackets"
    label='Spectral Initial Brackets'
    version="2.89.0"
    description='CACE production release: Spectral Initial Brackets.'
    evidence_kind=CAP["289"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v3 Production",description,Maturity.EXPERIMENTAL,
        assumptions=("Preserve theorem/evidence scope and refuse unsupported promotion.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Campaign result scope is explicit in returned artifact."])

def register_production_v289(registry):
    registry.register(ProductionV289)
