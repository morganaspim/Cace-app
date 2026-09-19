from __future__ import annotations

from fractions import Fraction
import hashlib
import json
from typing import Any

from cace_studio.modules.flux_v126_130_common import (
    F,
    dot,
    hdiv_topology,
    triangle_area,
    p1_grad_on_triangle,
    rt0_vector_at,
)


KERNEL_NAME = "CACE-P1-RT0-Discrete-Green-Exact-Checker"
KERNEL_VERSION = "1.0.0"


def _local_rt0_coefficients(topo: dict[str, Any], global_edge_flux_dofs, cell: int):
    return [
        F(sign) * F(global_edge_flux_dofs[eid])
        for eid, sign in zip(topo["cell_edges"][cell], topo["cell_signs"][cell])
    ]


def build_exact_green_artifact(points, triangles, nodal_values, global_edge_flux_dofs):
    """Build the minimal rational P1/RT0 data consumed by the independent checker."""
    canonical = {
        "points": [[str(F(x)), str(F(y))] for x, y in points],
        "triangles": [list(map(int, tri)) for tri in triangles],
        "nodal_values": [str(F(v)) for v in nodal_values],
        "global_edge_flux_dofs": [str(F(q)) for q in global_edge_flux_dofs],
    }
    canonical["input_sha256"] = hashlib.sha256(
        json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return canonical


def check_exact_discrete_green(artifact: dict[str, Any]) -> dict[str, Any]:
    """Independently check the elementwise and assembled P1/RT0 Green identity.

    For every affine triangle K this checks exactly
      int_K sigma.grad(v) + int_K div(sigma) v
        = int_boundary(K) v sigma.n.
    Shared global RT0 edge DOFs and continuous P1 nodal values then make interior
    edge contributions cancel exactly.  No continuum-space or Lean claim is made.
    """
    errors: list[str] = []
    points = [tuple(map(F, p)) for p in artifact.get("points", [])]
    triangles = [tuple(map(int, t)) for t in artifact.get("triangles", [])]
    nodal_values = [F(v) for v in artifact.get("nodal_values", [])]
    global_q = [F(q) for q in artifact.get("global_edge_flux_dofs", [])]

    if not points or len(nodal_values) != len(points):
        errors.append("mesh/nodal dimensions invalid")
    try:
        topo = hdiv_topology(points, triangles) if not errors else None
    except Exception as exc:
        topo = None
        errors.append(f"topology invalid: {exc}")
    if topo is not None and len(global_q) != len(topo["edges"]):
        errors.append("global RT0 edge-DOF dimension invalid")

    cell_records = []
    interior_edge_sum = {}
    boundary_edge_sum = {}
    global_volume = Fraction(0)
    global_divergence = Fraction(0)
    global_boundary = Fraction(0)

    if topo is not None and not errors:
        for k, tri in enumerate(triangles):
            area = triangle_area([points[i] for i in tri])
            vals = [nodal_values[i] for i in tri]
            grad = p1_grad_on_triangle(points, tri, nodal_values)
            coeff = _local_rt0_coefficients(topo, global_q, k)

            # RT0 is affine, so its cell average is its centroid value.
            centroid = (
                sum(points[i][0] for i in tri) / 3,
                sum(points[i][1] for i in tri) / 3,
            )
            sigma_c = rt0_vector_at(points, tri, coeff, centroid)
            volume = area * dot(sigma_c, grad)

            # Each local RT0 basis has integrated divergence one; hence
            # div(sigma) is constant and its cell integral is sum(coeff).
            integrated_div = sum(coeff, Fraction(0))
            mean_v = sum(vals, Fraction(0)) / 3
            divergence_term = integrated_div * mean_v

            boundary = Fraction(0)
            local_edges = ((tri[1], tri[2]), (tri[2], tri[0]), (tri[0], tri[1]))
            edge_terms = []
            for local_i, (u, v) in enumerate(local_edges):
                # coeff[local_i] is the outward integrated normal flux on this cell.
                # sigma.n is constant on a straight RT0 edge and P1 v is affine,
                # so multiplying by the endpoint average integrates the product exactly.
                term = coeff[local_i] * (nodal_values[u] + nodal_values[v]) / 2
                boundary += term
                eid = topo["cell_edges"][k][local_i]
                edge_terms.append({"edge_id": eid, "term": str(term)})
                target = interior_edge_sum if len(topo["edges"][eid]["cells"]) == 2 else boundary_edge_sum
                target[eid] = target.get(eid, Fraction(0)) + term

            residual = volume + divergence_term - boundary
            if residual != 0:
                errors.append(f"cell {k} Green residual is {residual}")
            global_volume += volume
            global_divergence += divergence_term
            global_boundary += boundary
            cell_records.append({
                "cell": k,
                "volume_pairing": str(volume),
                "divergence_pairing": str(divergence_term),
                "boundary_pairing": str(boundary),
                "residual": str(residual),
                "edge_terms": edge_terms,
            })

    interior_residual = sum(interior_edge_sum.values(), Fraction(0))
    if any(v != 0 for v in interior_edge_sum.values()):
        errors.append("assembled interior-edge cancellation failed")
    assembled_residual = global_volume + global_divergence - global_boundary
    if assembled_residual != 0:
        errors.append(f"assembled Green residual is {assembled_residual}")

    canonical = {k: artifact[k] for k in sorted(artifact)}
    return {
        "passed": not errors,
        "errors": errors,
        "checker": KERNEL_NAME,
        "checker_version": KERNEL_VERSION,
        "artifact_sha256": hashlib.sha256(
            json.dumps(canonical, sort_keys=True, separators=(",", ":"), default=str).encode()
        ).hexdigest(),
        "scope": "exact rational affine triangles; continuous P1 scalar field; global RT0 flux",
        "evidence_class": "rigorous exact computation; not Lean/kernel FORMAL evidence",
        "cell_records": cell_records,
        "global_volume_pairing": str(global_volume),
        "global_divergence_pairing": str(global_divergence),
        "global_boundary_pairing": str(global_boundary),
        "interior_edge_residual": str(interior_residual),
        "assembled_green_residual": str(assembled_residual),
        "interior_edge_terms": {str(k): str(v) for k, v in sorted(interior_edge_sum.items())},
        "boundary_edge_terms": {str(k): str(v) for k, v in sorted(boundary_edge_sum.items())},
    }
