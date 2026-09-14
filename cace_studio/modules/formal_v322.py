from __future__ import annotations
import hashlib, json
from pathlib import Path

from cace_studio.modules.formal_v301_320_common import *
from cace_studio.core.mesh_orthogonality_bridge import invoke_mesh_orthogonality_checker
from cace_studio.modules.formal_v321 import (
    local_lean_toolchain_probe,
    mesh_orthogonality_artifact,
    uploaded_lean_assets_assessment,
)


def concrete_mesh_certificate_artifact():
    artifact = mesh_orthogonality_artifact()
    artifact["theorem_id"] = "concrete-mesh-certificate-prager-synge-v3.22"
    artifact["lean_module"] = "CACEFormal.ConcreteMeshCertificate"
    artifact["lean_theorems"] = [
        "CACEFormal.v322_global_green_identity",
        "CACEFormal.v322_concrete_mesh_orthogonality",
        "CACEFormal.v322_discrete_prager_synge_from_concrete_mesh",
    ]
    artifact["scope"] = (
        "fixed rational square-with-center P1/constant-RT0-error mesh "
        "certificate represented in Lean"
    )
    return artifact


def concrete_mesh_certificate_to_prager_synge():
    artifact = concrete_mesh_certificate_artifact()
    check = invoke_mesh_orthogonality_checker(artifact)

    broken_boundary = json.loads(json.dumps(artifact))
    broken_boundary["primal_nodal_values"][0] = "1/7"
    bad_boundary = invoke_mesh_orthogonality_checker(broken_boundary)

    broken_flux = json.loads(json.dumps(artifact))
    broken_flux["flux_error_cell_vectors"][1] = ["2", "0"]
    bad_flux = invoke_mesh_orthogonality_checker(broken_flux)

    root = Path(__file__).resolve().parents[2]
    formal = root / "formal" / "cace_formal"
    concrete_source = formal / "CACEFormal" / "ConcreteMeshCertificate.lean"
    bridge_source = formal / "CACEFormal" / "DiscreteOrthogonality.lean"

    concrete_text = concrete_source.read_text() if concrete_source.exists() else ""
    bridge_text = bridge_source.read_text() if bridge_source.exists() else ""
    forbidden_markers = ("sorry", "admit", "OPEN OBLIGATION")

    required_theorems = [
        "theorem v322_global_green_identity",
        "theorem v322_concrete_mesh_orthogonality",
        "theorem v322_discrete_prager_synge_from_concrete_mesh",
        "theorem mesh_admissibility_to_orthogonality",
    ]
    lean_source_closed = (
        all(t in (concrete_text + bridge_text) for t in required_theorems)
        and not any(marker in concrete_text for marker in forbidden_markers)
        and not any(marker in bridge_text for marker in forbidden_markers)
    )

    tool = local_lean_toolchain_probe()
    payload = {
        "release": "3.22.0",
        "artifact": artifact,
        "exact_checker": check,
        "negative_tests": {
            "nonzero_boundary_rejected": not bool(bad_boundary.get("passed")),
            "normal_discontinuity_rejected": not bool(bad_flux.get("passed")),
        },
        "lean_concrete_mesh_certificate_closed": lean_source_closed,
        "lean_theorems": artifact["lean_theorems"],
        "orthogonality_derived_not_assumed": bool(
            check.get("orthogonality_derived_not_assumed")
        ),
        "lean_toolchain": tool,
        "uploaded_lean_assets": uploaded_lean_assets_assessment(),
        "lean_external_build_status": (
            "READY_TO_RUN" if tool.get("lean") and tool.get("lake") else "NOT_RUN"
        ),
        "full_external_machine_formal": False,
        "scope": (
            "Concrete fixed rational P1/constant-RT0-error mesh certificate "
            "is represented in Lean and feeds the generic discrete Prager-Synge bridge."
        ),
        "nonclaims": [
            "Continuum H1/H(div) trace and general unstructured-mesh FEM remain open.",
            "External machine-formal status still requires pinned lake build success.",
        ],
    }
    payload["pass"] = (
        bool(check.get("passed"))
        and all(payload["negative_tests"].values())
        and payload["orthogonality_derived_not_assumed"]
        and lean_source_closed
    )
    payload["sha256"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()
    return payload


class FormalV322(FormalStepModule):
    capability_key = "322"
    module_id = "formal322.concrete_mesh_certificate_prager_synge"
    label = "Concrete Mesh Certificate Prager-Synge"
    version = "3.22.0"
    description = (
        "Represent the fixed rational square-with-center P1/constant-RT0-error "
        "mesh certificate in Lean and derive the discrete Prager-Synge endpoint."
    )
    evidence_kind = EvidenceKind.SYMBOLIC
    metadata = ModuleMetadata(
        module_id,
        label,
        version,
        "CACE Formal",
        description,
        Maturity.EXPERIMENTAL,
        assumptions=(
            "General continuum H1/H(div) traces are outside v3.22 scope.",
            "External Lean promotion requires a successful pinned lake build.",
        ),
    )
    proof_status = ProofStatus(
        evidence={evidence_kind},
        unit_tests=True,
        regression_tests=True,
        documentation=True,
        limitations=[
            "The Lean certificate is a concrete finite rational fixture, not a "
            "general mesh generator theorem."
        ],
    )

    def execute(self, inputs, params, ctx):
        return {"result": concrete_mesh_certificate_to_prager_synge()}


def register_formal_v322(registry):
    registry.register(FormalV322)
