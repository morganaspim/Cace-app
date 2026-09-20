from __future__ import annotations

from typing import Any, Mapping

from cace_studio.core.formal_runtime_packet import (
    build_p1_rt0_runtime_packet,
    render_lean_p1_rt0_binding,
    verify_p1_rt0_runtime_packet,
)
from cace_studio.core.formal_source_binding import (
    create_formal_source_binding,
    verify_formal_source_binding,
)
from cace_studio.core.module import ExecutionContext, Module, ValidationError
from cace_studio.core.types import (
    EvidenceKind,
    Maturity,
    ModuleMetadata,
    ParameterSpec,
    PortSpec,
    ProofStatus,
)
from cace_studio.core.verification import VerificationRecord, VerificationState


class P1RT0FormalRuntimePacket(Module):
    metadata = ModuleMetadata(
        module_id="formal_bridge.p1_rt0_runtime_packet",
        name="P1/RT0 Exact Runtime → Lean Source Binding",
        version="1.0.0",
        category="Formal Runtime Bridge",
        description=(
            "Build a content-addressed exact-rational mesh/P1/RT0 packet and emit "
            "deterministic Lean source for MeshCertificate, P1Affine, and RT0Affine."
        ),
        maturity=Maturity.EXPERIMENTAL,
        assumptions=(
            "Geometry and coefficients are supplied as integers or exact rational strings.",
            "The runtime P1 convention is c + gx*x + gy*y on each triangle.",
            "The runtime RT0 convention is (cx + radial*x, cy + radial*y) on each triangle.",
            "Formal verification requires a later pinned Lean build and canonical qualification path.",
        ),
    )
    inputs = (PortSpec("runtime_data", "mapping"),)
    outputs = (
        PortSpec("runtime_packet", "mapping"),
        PortSpec("lean_source", "text"),
        PortSpec("source_binding", "mapping"),
    )
    parameters = (
        ParameterSpec(
            "mesh_definition_name",
            "text",
            "studioRuntimeMesh",
            "Simple Lean identifier for the generated MeshCertificate.",
        ),
        ParameterSpec(
            "binding_prefix",
            "text",
            "studioRuntimeP1RT0",
            "Simple Lean identifier prefix for generated P1/RT0 definitions.",
        ),
    )
    proof_status = ProofStatus(
        evidence={EvidenceKind.SYMBOLIC},
        unit_tests=True,
        property_tests=False,
        regression_tests=True,
        documentation=True,
        formal_artifact="CACEFormal.MeshCertificate / P1Affine / RT0Affine generated source",
        limitations=[
            "PASS from this module means deterministic exact packet/source binding only.",
            "FSL-2/FSL-3/FSL-4 remain GENERATED_NOT_BUILT until pinned Lean compilation succeeds.",
            "FSL-5 through FSL-13 remain unresolved.",
            "No continuum H1/H(div), volumePairing, trace, or Prager-Synge runtime claim is made.",
            "Binary floating-point inputs are rejected rather than rounded or silently reinterpreted.",
        ],
    )

    def validate(self, inputs, params):
        super().validate(inputs, params)
        data = inputs.get("runtime_data")
        if not isinstance(data, Mapping):
            raise ValidationError("runtime_data must be a mapping")
        for key in ("mesh", "p1_cells", "rt0_cells"):
            if key not in data:
                raise ValidationError(f"runtime_data missing {key!r}")

    def execute(
        self,
        inputs: Mapping[str, Any],
        params: Mapping[str, Any],
        ctx: ExecutionContext,
    ) -> Mapping[str, Any]:
        data = inputs["runtime_data"]
        mesh_definition_name = str(params.get("mesh_definition_name", "studioRuntimeMesh"))
        binding_prefix = str(params.get("binding_prefix", "studioRuntimeP1RT0"))

        packet = build_p1_rt0_runtime_packet(
            data["mesh"],
            data["p1_cells"],
            data["rt0_cells"],
            source_identity={
                "module_id": self.metadata.module_id,
                "module_version": self.metadata.version,
            },
        )
        lean_source = render_lean_p1_rt0_binding(
            packet,
            mesh_definition_name=mesh_definition_name,
            binding_prefix=binding_prefix,
        )
        source_binding = create_formal_source_binding(
            packet,
            lean_source,
            mesh_definition_name=mesh_definition_name,
            binding_prefix=binding_prefix,
        )
        source_binding["run_id"] = ctx.run_id
        return {
            "runtime_packet": packet,
            "lean_source": lean_source,
            "source_binding": source_binding,
        }

    def verify(self, inputs, params, outputs, ctx):
        packet = outputs.get("runtime_packet")
        lean_source = outputs.get("lean_source")
        binding = outputs.get("source_binding")

        packet_check = verify_p1_rt0_runtime_packet(packet)
        binding_for_check = dict(binding) if isinstance(binding, Mapping) else {}
        binding_for_check.pop("run_id", None)
        binding_check = verify_formal_source_binding(
            binding_for_check,
            packet,
            lean_source,
        ) if packet_check["passed"] and isinstance(lean_source, str) else {
            "passed": False,
            "errors": ["packet or Lean source invalid"],
        }

        state = (
            VerificationState.PASS
            if packet_check["passed"] and binding_check["passed"]
            else VerificationState.FAIL
        )
        return [
            VerificationRecord(
                verifier="formal_bridge.p1_rt0_runtime_packet.exact_source_binding",
                kind=EvidenceKind.SYMBOLIC,
                claim=(
                    "The runtime mesh/P1/RT0 data has a deterministic exact-rational "
                    "packet and content-addressed generated Lean source binding."
                ),
                state=state,
                method="exact Fraction normalization + deterministic regeneration + SHA-256 binding",
                metrics={
                    "packet_sha256": packet.get("packet_sha256") if isinstance(packet, Mapping) else None,
                    "mesh_certificate_sha256": (
                        packet.get("mesh_certificate", {}).get("sha256")
                        if isinstance(packet, Mapping)
                        else None
                    ),
                    "lean_source_sha256": binding_for_check.get("lean_source_sha256"),
                    "lean_build_state": "NOT_RUN",
                    "qualification_state": "NOT_RUN",
                    "fsl_2_4": "GENERATED_NOT_BUILT",
                    "fsl_5_13": "UNRESOLVED",
                },
                notes=(
                    "This verifier intentionally emits SYMBOLIC rather than FORMAL evidence.",
                    "Generated source must still pass the pinned Lean and canonical qualification path.",
                ),
            )
        ]


def register_p1_rt0_formal_bridges(registry):
    registry.register(P1RT0FormalRuntimePacket)
