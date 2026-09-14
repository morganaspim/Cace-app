from cace_studio.modules.production_v251_300_common import *

class ProductionV252(ProductionStepModule):
    capability_key="252"
    module_id="prod252.rt1_piola_and_orientation"
    label='RT1 Piola and Orientation'
    version="2.52.0"
    description='CACE production release: RT1 Piola and Orientation.'
    evidence_kind=CAP["252"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v3 Production",description,Maturity.EXPERIMENTAL,
        assumptions=("Preserve theorem/evidence scope and refuse unsupported promotion.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Campaign result scope is explicit in returned artifact."])

def register_production_v252(registry):
    registry.register(ProductionV252)
