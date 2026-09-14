from __future__ import annotations
from typing import Any, Mapping
from cace_studio.core.module import Module, ExecutionContext
from cace_studio.core.types import *

class Constant(Module):
    metadata = ModuleMetadata("core.constant", "Constant", "1.0.0", "Utilities", "Emit a constant value.", Maturity.BETA)
    outputs = (PortSpec("value", "number"),)
    parameters = (ParameterSpec("value", "number", 0.0, "Value to emit"),)
    proof_status = ProofStatus(evidence={EvidenceKind.NUMERICAL}, unit_tests=True, documentation=True)
    def execute(self, inputs, params, ctx): return {"value": params["value"]}

class Add(Module):
    metadata = ModuleMetadata("core.add", "Add", "1.0.0", "Linear Algebra", "Add two scalar values.", Maturity.BETA,
                              assumptions=("Inputs support exact Python addition semantics.",))
    inputs = (PortSpec("a", "number"), PortSpec("b", "number"))
    outputs = (PortSpec("sum", "number"),)
    proof_status = ProofStatus(evidence={EvidenceKind.NUMERICAL}, unit_tests=True, property_tests=True, documentation=True)
    def execute(self, inputs, params, ctx): return {"sum": inputs["a"] + inputs["b"]}

def register_builtins(registry):
    registry.register(Constant); registry.register(Add)
