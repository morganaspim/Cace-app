from __future__ import annotations

import json
from typing import Any, Mapping

from cace_studio.core.mesh_certificate import (
    generate_mesh_certificate,
    render_lean_mesh_certificate,
    verification_chain,
    verify_mesh_certificate,
)
from cace_studio.core.module import ExecutionContext, Module
from cace_studio.core.types import (
    EvidenceKind,
    Maturity,
    ModuleMetadata,
    ParameterSpec,
    PortSpec,
    ProofStatus,
)
from cace_studio.core.verification import VerificationRecord, VerificationState


_DEFAULT_MESH_JSON = json.dumps(
    {
        "vertices": [["0", "0"], ["1", "0"], ["1", "1"], ["0", "1"], ["1/2", "1/2"]],
        "triangles": [[0, 1, 4], [1, 2, 4], [2, 3, 4], [3, 0, 4]],
        "boundary_labels": {"0-1": "bottom", "1-2": "right", "2-3": "top", "0-3": "left"},
    },
    sort_keys=True,
)


class MeshCertificateGeneratorV325(Module):
    metadata = ModuleMetadata(
        module_id="formal325.mesh_certificate_generator",
        name="Mesh Certificate Generator",
        version="3.25.0",
        category="CACE Formal",
        description=(
            "Generate an exact rational triangular MeshCertificate payload, run an "
            "independent exact regeneration checker, and emit a closed Lean witness source."
        ),
        maturity=Maturity.EXPERIMENTAL,
        assumptions=(
            "Input triangles are intended to be counter-clockwise.",
            "Formal verification of a generated witness requires the pinned Lean CI gate to pass.",
            "Continuum H1/H(div) closure is outside v3.25 scope.",
        ),
    )
    inputs = (PortSpec("mesh", "mapping", required=False),)
    outputs = (
        PortSpec("certificate", "mapping"),
        PortSpec("lean_source", "text"),
        PortSpec("verification_chain", "mapping"),
    )
    parameters = (
        ParameterSpec(
            "mesh_json",
            "text",
            _DEFAULT_MESH_JSON,
            "Exact mesh JSON used when no mesh is connected to the input port.",
        ),
        ParameterSpec(
            "definition_name",
            "text",
            "studioGeneratedMesh",
            "Simple Lean identifier used for the generated MeshCertificate definition.",
        ),
    )
    proof_status = ProofStatus(
        evidence={EvidenceKind.SYMBOLIC},
        unit_tests=True,
        property_tests=False,
        regression_tests=True,
        documentation=True,
        formal_artifact="CACEFormal.MeshCertificate",
        limitations=[
            "Python exact-checker PASS is symbolic/exact evidence, not machine-formal Lean evidence.",
            "Generated Lean becomes formally verified only after the pinned CI build passes.",
            "The Lean renderer currently requires at least one interior and one boundary edge.",
        ],
    )

    def execute(
        self,
        inputs: Mapping[str, Any],
        params: Mapping[str, Any],
        ctx: ExecutionContext,
    ) -> Mapping[str, Any]:
        mesh = inputs.get("mesh")
        if mesh is None:
            try:
                mesh = json.loads(str(params.get("mesh_json", _DEFAULT_MESH_JSON)))
            except json.JSONDecodeError as exc:
                raise ValueError(f"mesh_json is not valid JSON: {exc}") from exc
        if not isinstance(mesh, Mapping):
            raise ValueError("mesh input must be a mapping")
        cert = generate_mesh_certificate(
            mesh.get("vertices", []),
            mesh.get("triangles", []),
            mesh.get("boundary_labels", {}),
        )
        check = verify_mesh_certificate(cert)
        if not check["passed"]:
            raise ValueError("generated certificate failed independent exact regeneration")
        lean_source = render_lean_mesh_certificate(
            cert, str(params.get("definition_name", "studioGeneratedMesh"))
        )
        chain = verification_chain(cert)
        chain["run_id"] = ctx.run_id
        return {
            "certificate": cert,
            "lean_source": lean_source,
            "verification_chain": chain,
        }

    def verify(self, inputs, params, outputs, ctx):
        check = verify_mesh_certificate(outputs["certificate"])
        return [
            VerificationRecord(
                verifier="cace_studio.core.mesh_certificate.verify_mesh_certificate",
                kind=EvidenceKind.SYMBOLIC,
                claim=(
                    "The emitted finite triangular mesh certificate exactly regenerates, has "
                    "positive signed Jacobians, canonical edge ownership, and opposite interior orientations."
                ),
                state=(VerificationState.PASS if check["passed"] else VerificationState.FAIL),
                method="independent exact Fraction regeneration and SHA-256 payload check",
                metrics={
                    "certificate_sha256": outputs["certificate"].get("sha256"),
                    "counts": outputs["certificate"].get("counts", {}),
                    "lean_ci": "NOT_RUN",
                },
                notes=(
                    "This record intentionally remains symbolic rather than FORMAL until Lean CI passes for the emitted witness.",
                ),
            )
        ]


def register_formal_v325(registry):
    registry.register(MeshCertificateGeneratorV325)
