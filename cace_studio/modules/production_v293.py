from cace_studio.modules.production_v251_300_common import *

class ProductionV293(ProductionStepModule):
    capability_key="293"
    module_id="prod293.production_solver_family_interface"
    label='Production Solver Family Interface'
    version="2.93.0"
    description='CACE production release: Production Solver Family Interface.'
    evidence_kind=CAP["293"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v3 Production",description,Maturity.EXPERIMENTAL,
        assumptions=("Preserve theorem/evidence scope and refuse unsupported promotion.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Campaign result scope is explicit in returned artifact."])

def register_production_v293(registry):
    registry.register(ProductionV293)
