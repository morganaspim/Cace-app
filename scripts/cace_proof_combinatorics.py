#!/usr/bin/env python3
"""Combinatorial proof-synthesis search for CACE formal modules.

The search is intentionally conservative: it does not claim a theorem merely
because files can be imported together.  Each capability group declares what
it *provides*, what it *requires*, and whether any capability is only a fixture
or placeholder.  Candidate k-way combinations are ranked by closure of named
proof targets.

This is a discovery/planning tool.  Lean remains the authority that validates
every promoted theorem.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from itertools import combinations
import argparse
import json
from typing import FrozenSet, Iterable


@dataclass(frozen=True)
class Group:
    name: str
    modules: tuple[str, ...]
    provides: FrozenSet[str]
    requires: FrozenSet[str] = frozenset()
    provisional: FrozenSet[str] = frozenset()


@dataclass(frozen=True)
class Target:
    name: str
    requires: FrozenSet[str]
    payoff: int
    suggested_module: str


GROUPS: tuple[Group, ...] = (
    Group(
        "fiber_geometry",
        (
            "ReferenceSimplexFiber",
            "ReferenceSimplexFiberDomain",
            "ReferenceSimplexFiberDecomposition",
            "ReferenceSimplexEndpointGeometry",
        ),
        frozenset({
            "fiber_interval",
            "fiber_base_domain",
            "endpoint_on_facets",
        }),
    ),
    Group(
        "fiber_measure",
        (
            "ReferenceSimplexFiberMeasure",
            "ReferenceSimplexFubini",
            "ReferenceSimplexIntegrability",
        ),
        frozenset({
            "orthogonal_fubini",
            "fiber_integrability",
        }),
        frozenset({"fiber_interval"}),
    ),
    Group(
        "fiber_calculus",
        (
            "ReferenceSimplexFiberCalculus",
            "ReferenceSimplexFiberIBP",
            "ReferenceSimplexEndpointIBP",
            "ReferenceSimplexCoordinateGreen",
        ),
        frozenset({
            "fiber_derivatives",
            "fiber_ibp",
            "coordinate_green",
        }),
        frozenset({"fiber_interval", "fiber_integrability"}),
    ),
    Group(
        "reference_facet_geometry",
        (
            "ReferenceSimplexGeometry",
            "ReferenceSimplexCell",
            "ReferenceSimplexFacets",
        ),
        frozenset({
            "reference_geometric_simplex",
            "reference_cell_identification",
            "facet_equations",
        }),
    ),
    Group(
        "coordinate_facet",
        (
            "ReferenceSimplexCoordinateFacetMeasure",
            "ReferenceSimplexCoordinateFacetNormal",
            "ReferenceSimplexCoordinateFacetCurrent",
        ),
        frozenset({
            "coordinate_surface_measure",
            "coordinate_outward_normal",
            "coordinate_facet_current",
        }),
        frozenset({
            "facet_equations",
            "endpoint_on_facets",
            "facet_current_distribution",
        }),
    ),
    Group(
        "top_facet",
        (
            "ReferenceSimplexTopFacetParameterization",
            "ReferenceSimplexTopFacetJacobian",
            "ReferenceSimplexTopFacetNormal",
            "ReferenceSimplexTopFacetFluxFactor",
        ),
        frozenset({
            "top_parameterization",
            "top_surface_jacobian",
            "top_outward_normal",
            "top_flux_factor",
        }),
        frozenset({
            "facet_equations",
            "endpoint_on_facets",
        }),
    ),
    Group(
        "facet_currents",
        (
            "SimplexFacetGeometry",
            "SimplexFacetMeasure",
            "SimplexFacetCurrent",
            "SimplexBoundaryDistribution",
        ),
        frozenset({
            "facet_current_distribution",
            "finite_facet_measure",
            "oriented_facet_normal",
        }),
    ),
    Group(
        "simplex_distribution_bridge",
        ("SimplexCellDistributionBridge",),
        frozenset({
            "cell_to_distribution_bridge",
            "assembled_h1_from_cell_ibp",
            "assembled_hdiv_from_cell_ibp",
        }),
        frozenset({
            "local_p1_cell_ibp",
            "local_rt0_cell_ibp",
            "boundary_sum_zero",
        }),
    ),
    Group(
        "mesh_cancellation",
        (
            "MeshCombinatorics",
            "MeshFaceAssembly",
            "PiecewiseInterfaceCancellation",
            "PiecewiseDistributionalRepresentatives",
            "RT0P1Assembly",
            "RT0P1DerivedAssembly",
        ),
        frozenset({
            "matching_trace_cancellation",
            "opposite_normal_cancellation",
            "boundary_sum_zero",
        }),
        frozenset({"facet_current_distribution"}),
    ),
    Group(
        "graph_representatives",
        (
            "DistributionalGraphRepresentatives",
            "ContinuumGraphSpaces",
            "H1DomainBridge",
            "H1GraphConverse",
        ),
        frozenset({
            "h1_graph_representative",
            "hdiv_graph_representative",
            "graph_predicate_bridge",
        }),
        frozenset({"assembled_h1_from_cell_ibp", "assembled_hdiv_from_cell_ibp"}),
    ),
    Group(
        "graph_density",
        (
            "GraphDensity",
            "GraphClosedSpaces",
            "GraphRegularizationCriterion",
            "RegularizationClosure",
        ),
        frozenset({
            "smooth_h1_graph_density",
            "smooth_hdiv_graph_density",
            "closed_graph_regularization",
        }),
    ),
    Group(
        "weak_green",
        (
            "GraphGreenPairing",
            "WeakGreenFunctional",
            "ContinuumOrthogonality",
        ),
        frozenset({
            "bounded_green_pairing",
            "zero_boundary_orthogonality",
        }),
        frozenset({
            "h1_graph_representative",
            "hdiv_graph_representative",
            "smooth_h1_graph_density",
            "smooth_hdiv_graph_density",
        }),
    ),
    Group(
        "prager_synge",
        (
            "AbstractPragerSynge",
            "ContinuumPragerSynge",
            "Hypercircle",
        ),
        frozenset({
            "prager_synge_identity",
            "hypercircle_closure",
        }),
        frozenset({"zero_boundary_orthogonality"}),
    ),
    Group(
        "affine_transport",
        ("Piola",),
        frozenset({"diagonal_piola_fixture"}),
        provisional=frozenset({"general_affine_piola"}),
    ),
    Group(
        "weighted_energy",
        ("WeightedEnergy",),
        frozenset({"weighted_energy_assumptions"}),
        provisional=frozenset({"concrete_weighted_energy_operator"}),
    ),
)


TARGETS: tuple[Target, ...] = (
    Target(
        "top_facet_current",
        frozenset({
            "top_parameterization",
            "top_surface_jacobian",
            "top_outward_normal",
            "top_flux_factor",
            "facet_current_distribution",
        }),
        90,
        "ReferenceSimplexTopFacetCurrent",
    ),
    Target(
        "reference_p1_cell_ibp",
        frozenset({
            "coordinate_green",
            "coordinate_facet_current",
            "top_facet_current",
            "cell_to_distribution_bridge",
        }),
        120,
        "ReferenceSimplexP1CellIBP",
    ),
    Target(
        "reference_rt0_cell_ibp",
        frozenset({
            "coordinate_green",
            "coordinate_facet_current",
            "top_facet_current",
            "cell_to_distribution_bridge",
        }),
        120,
        "ReferenceSimplexRT0CellIBP",
    ),
    Target(
        "mesh_h1_hdiv_closure",
        frozenset({
            "local_p1_cell_ibp",
            "local_rt0_cell_ibp",
            "boundary_sum_zero",
            "cell_to_distribution_bridge",
        }),
        160,
        "SimplexMeshGraphClosure",
    ),
    Target(
        "continuum_prager_synge_from_mesh",
        frozenset({
            "assembled_h1_from_cell_ibp",
            "assembled_hdiv_from_cell_ibp",
            "h1_graph_representative",
            "hdiv_graph_representative",
            "smooth_h1_graph_density",
            "smooth_hdiv_graph_density",
            "zero_boundary_orthogonality",
            "prager_synge_identity",
        }),
        240,
        "CertifiedContinuumPragerSynge",
    ),
    Target(
        "general_affine_simplex_transport",
        frozenset({
            "local_p1_cell_ibp",
            "local_rt0_cell_ibp",
            "general_affine_piola",
        }),
        200,
        "AffineSimplexGaussGreenTransport",
    ),
)


DERIVED_RULES: tuple[tuple[FrozenSet[str], FrozenSet[str]], ...] = (
    (
        frozenset({
            "top_parameterization",
            "top_surface_jacobian",
            "top_outward_normal",
            "top_flux_factor",
            "facet_current_distribution",
        }),
        frozenset({"top_facet_current"}),
    ),
    (
        frozenset({
            "coordinate_green",
            "coordinate_facet_current",
            "top_facet_current",
            "cell_to_distribution_bridge",
        }),
        frozenset({"local_p1_cell_ibp", "local_rt0_cell_ibp"}),
    ),
    (
        frozenset({
            "local_p1_cell_ibp",
            "local_rt0_cell_ibp",
            "boundary_sum_zero",
            "cell_to_distribution_bridge",
        }),
        frozenset({
            "assembled_h1_from_cell_ibp",
            "assembled_hdiv_from_cell_ibp",
        }),
    ),
    (
        frozenset({
            "assembled_h1_from_cell_ibp",
            "assembled_hdiv_from_cell_ibp",
            "h1_graph_representative",
            "hdiv_graph_representative",
            "smooth_h1_graph_density",
            "smooth_hdiv_graph_density",
            "zero_boundary_orthogonality",
            "prager_synge_identity",
        }),
        frozenset({"certified_continuum_prager_synge"}),
    ),
)


def closure(seed: Iterable[str]) -> frozenset[str]:
    facts = set(seed)
    changed = True
    while changed:
        changed = False
        for req, out in DERIVED_RULES:
            if req <= facts and not out <= facts:
                facts.update(out)
                changed = True
    return frozenset(facts)


def evaluate_combo(groups: tuple[Group, ...]) -> dict:
    provided = closure(x for g in groups for x in g.provides)
    required = frozenset(x for g in groups for x in g.requires)
    provisional = frozenset(x for g in groups for x in g.provisional)

    internally_satisfied = required & provided
    unsatisfied = required - provided
    hits = []
    score = 10 * len(groups) + 3 * len(internally_satisfied) - 8 * len(unsatisfied)
    score -= 25 * len(provisional)

    for target in TARGETS:
        missing = target.requires - provided
        coverage = len(target.requires & provided)
        if not missing:
            score += target.payoff
            hits.append({
                "target": target.name,
                "status": "closed",
                "suggested_module": target.suggested_module,
                "missing": [],
            })
        elif coverage:
            # Reward near-closures without pretending they are proofs.
            score += coverage * 4
            hits.append({
                "target": target.name,
                "status": "partial",
                "suggested_module": target.suggested_module,
                "missing": sorted(missing),
            })

    # Prefer combinations spanning genuinely different mathematical capabilities.
    score += 2 * len({g.name.split("_")[0] for g in groups})
    return {
        "groups": [g.name for g in groups],
        "modules": sorted({m for g in groups for m in g.modules}),
        "provided": sorted(provided),
        "required": sorted(required),
        "unsatisfied_internal_requirements": sorted(unsatisfied),
        "provisional_capabilities": sorted(provisional),
        "target_hits": hits,
        "score": score,
    }


def enumerate_ranked(min_k: int, max_k: int, top: int) -> list[dict]:
    rows = []
    for k in range(min_k, min(max_k, len(GROUPS)) + 1):
        for combo in combinations(GROUPS, k):
            row = evaluate_combo(combo)
            # Keep only mathematically connected combinations: at least one
            # target overlap or one internal requirement discharged.
            connected = any(x["status"] in {"closed", "partial"} for x in row["target_hits"])
            connected |= bool(
                set(row["required"]) & set(row["provided"])
            )
            if connected:
                rows.append(row)
    rows.sort(
        key=lambda r: (
            -r["score"],
            len(r["unsatisfied_internal_requirements"]),
            len(r["groups"]),
            r["groups"],
        )
    )
    return rows[:top]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--min-k", type=int, default=2)
    parser.add_argument("--max-k", type=int, default=6)
    parser.add_argument("--top", type=int, default=30)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    if args.min_k < 2:
        raise SystemExit("--min-k must be at least 2")
    rows = enumerate_ranked(args.min_k, args.max_k, args.top)
    payload = {
        "schema": "cace-proof-combinatorics-v1",
        "group_count": len(GROUPS),
        "target_count": len(TARGETS),
        "search": {
            "min_k": args.min_k,
            "max_k": args.max_k,
            "top": args.top,
        },
        "results": rows,
        "note": (
            "This ranks proof candidates only. A target is not certified until "
            "the resulting Lean theorem passes the pinned kernel/audit path."
        ),
    }
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        for index, row in enumerate(rows, start=1):
            closed = [
                x["target"] for x in row["target_hits"] if x["status"] == "closed"
            ]
            partial = [
                x["target"] for x in row["target_hits"] if x["status"] == "partial"
            ]
            print(
                f"{index:2d}. score={row['score']:4d} "
                f"k={len(row['groups'])} groups={'+'.join(row['groups'])}"
            )
            if closed:
                print("    closes:", ", ".join(closed))
            if partial:
                print("    advances:", ", ".join(partial))
            if row["provisional_capabilities"]:
                print(
                    "    blocked/provisional:",
                    ", ".join(row["provisional_capabilities"]),
                )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
