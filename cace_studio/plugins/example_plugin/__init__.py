from cace_studio.core.module import Module
from cace_studio.core.types import ModuleMetadata, PortSpec, ProofStatus, Maturity, EvidenceKind

class Negate(Module):
    metadata = ModuleMetadata("example.negate", "Negate", "1.0.0", "Examples", "Negate a scalar.", Maturity.EXPERIMENTAL)
    inputs = (PortSpec("x", "number"),); outputs = (PortSpec("y", "number"),)
    proof_status = ProofStatus(evidence={EvidenceKind.NUMERICAL})
    def execute(self, inputs, params, ctx): return {"y": -inputs["x"]}

def register(registry): registry.register(Negate)
