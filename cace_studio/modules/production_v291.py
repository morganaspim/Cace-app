from cace_studio.modules.production_v251_300_common import *

class ProductionV291(ProductionStepModule):
    capability_key="291"
    module_id="prod291.lehmann_goerisch_fixture"
    label='Lehmann-Goerisch Fixture'
    version="2.91.0"
    description='CACE production release: Lehmann-Goerisch Fixture.'
    evidence_kind=CAP["291"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v3 Production",description,Maturity.EXPERIMENTAL,
        assumptions=("Preserve theorem/evidence scope and refuse unsupported promotion.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Campaign result scope is explicit in returned artifact."])

def register_production_v291(registry):
    registry.register(ProductionV291)
