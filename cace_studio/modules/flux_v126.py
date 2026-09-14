from cace_studio.modules.flux_v126_130_common import *

class FluxV126(FluxStepModule):
    capability_key="126"
    module_id="flux126.rt0_basis"
    label="RT0 Basis and Geometry"
    version="1.26.0"
    description="CACE equilibrated-flux step: RT0 Basis and Geometry."
    evidence_kind=CAP["126"][2]
    metadata=ModuleMetadata(module_id,label,version,"Equilibrated Flux",description,Maturity.EXPERIMENTAL,
        assumptions=("Conforming affine triangular mesh and declared flux/PDE conventions",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Reviewed external mathematics is not automatically formal evidence."])

def register_flux_v126(registry):
    registry.register(FluxV126)
