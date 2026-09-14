from cace_studio.modules.production_v251_300_common import *

class ProductionV258(ProductionStepModule):
    capability_key="258"
    module_id="prod258.3d_face_topology_and_orientation"
    label='3D Face Topology and Orientation'
    version="2.58.0"
    description='CACE production release: 3D Face Topology and Orientation.'
    evidence_kind=CAP["258"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v3 Production",description,Maturity.EXPERIMENTAL,
        assumptions=("Preserve theorem/evidence scope and refuse unsupported promotion.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Campaign result scope is explicit in returned artifact."])

def register_production_v258(registry):
    registry.register(ProductionV258)
