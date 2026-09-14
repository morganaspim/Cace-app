from cace_studio.modules.production_v251_300_common import *

class ProductionV259(ProductionStepModule):
    capability_key="259"
    module_id="prod259.3d_piola_rt0_audit"
    label='3D Piola RT0 Audit'
    version="2.59.0"
    description='CACE production release: 3D Piola RT0 Audit.'
    evidence_kind=CAP["259"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v3 Production",description,Maturity.EXPERIMENTAL,
        assumptions=("Preserve theorem/evidence scope and refuse unsupported promotion.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Campaign result scope is explicit in returned artifact."])

def register_production_v259(registry):
    registry.register(ProductionV259)
