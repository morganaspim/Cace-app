from cace_studio.modules.production_v251_300_common import *

class ProductionV264(ProductionStepModule):
    capability_key="264"
    module_id="prod264.3d_prager_synge_campaign"
    label='3D Prager-Synge Campaign'
    version="2.64.0"
    description='CACE production release: 3D Prager-Synge Campaign.'
    evidence_kind=CAP["264"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v3 Production",description,Maturity.EXPERIMENTAL,
        assumptions=("Preserve theorem/evidence scope and refuse unsupported promotion.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Campaign result scope is explicit in returned artifact."])

def register_production_v264(registry):
    registry.register(ProductionV264)
