from cace_studio.modules.production_v251_300_common import *

class ProductionV281(ProductionStepModule):
    capability_key="281"
    module_id="prod281.maxwell_exact_sequence"
    label='Maxwell Exact Sequence'
    version="2.81.0"
    description='CACE production release: Maxwell Exact Sequence.'
    evidence_kind=CAP["281"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v3 Production",description,Maturity.EXPERIMENTAL,
        assumptions=("Preserve theorem/evidence scope and refuse unsupported promotion.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Campaign result scope is explicit in returned artifact."])

def register_production_v281(registry):
    registry.register(ProductionV281)
