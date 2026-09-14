from cace_studio.modules.production_v251_300_common import *

class ProductionV251(ProductionStepModule):
    capability_key="251"
    module_id="prod251.rt1_global_dof_topology"
    label='RT1 Global DOF Topology'
    version="2.51.0"
    description='CACE production release: RT1 Global DOF Topology.'
    evidence_kind=CAP["251"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v3 Production",description,Maturity.EXPERIMENTAL,
        assumptions=("Preserve theorem/evidence scope and refuse unsupported promotion.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Campaign result scope is explicit in returned artifact."])

def register_production_v251(registry):
    registry.register(ProductionV251)
