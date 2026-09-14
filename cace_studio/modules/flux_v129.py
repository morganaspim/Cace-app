from cace_studio.modules.flux_v126_130_common import *

class FluxV129(FluxStepModule):
    capability_key="129"
    module_id="flux129.global_equilibrium"
    label="Global Equilibrium Verification"
    version="1.29.0"
    description="CACE equilibrated-flux step: Global Equilibrium Verification."
    evidence_kind=CAP["129"][2]
    metadata=ModuleMetadata(module_id,label,version,"Equilibrated Flux",description,Maturity.EXPERIMENTAL,
        assumptions=("Conforming affine triangular mesh and declared flux/PDE conventions",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Reviewed external mathematics is not automatically formal evidence."])

def register_flux_v129(registry):
    registry.register(FluxV129)
