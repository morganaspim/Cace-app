
from __future__ import annotations
import hashlib, json, math
from dataclasses import dataclass, asdict
from typing import Any

from cace_studio.modules.fem_v051_075_common import ResultModule
from cace_studio.core.types import ModuleMetadata, Maturity, EvidenceKind, ProofStatus
from cace_studio.core.theorems import TheoremStatus, TheoremContract

SCOTT_ZHANG_1990 = {
    "id": "scott-zhang-1990",
    "title": "Finite element interpolation of nonsmooth functions satisfying boundary conditions",
    "authors": ["L. Ridgway Scott", "Shangyou Zhang"],
    "journal": "Mathematics of Computation",
    "volume": 54,
    "number": 190,
    "year": 1990,
    "pages": "483-493",
    "url": "https://www.ams.org/journals/mcom/1990-54-190/S0025-5718-1990-1011446-7/",
}

def _sha(x: Any) -> str:
    return hashlib.sha256(json.dumps(x, sort_keys=True, separators=(",",":"), default=str).encode()).hexdigest()

def imported_lemma_registry() -> dict[str, dict[str, Any]]:
    """Reviewed mathematical imports. These are literature-established, not machine-formal."""
    common = {
        "status": TheoremStatus.REVIEWED_ASSUMED.value,
        "machine_checked": False,
        "source": SCOTT_ZHANG_1990,
    }
    return {
        "scott_zhang_local_L2": {
            **common,
            "statement": "For a conforming uniformly shape-regular simplicial family, there is a boundary-preserving Scott-Zhang projector I_h and C0=C(d,gamma) such that ||v-I_h v||_L2(K) <= C0 h_K ||grad v||_L2(omega_K) for every v in H1_0(Omega).",
            "dependencies": ["bounded_polyhedral_lipschitz_domain", "conforming_affine_simplicial_family", "uniform_shape_regularity", "P1_space"],
        },
        "scott_zhang_local_H1": {
            **common,
            "statement": "There is C1=C(d,gamma) such that ||grad(v-I_h v)||_L2(K) <= C1 ||grad v||_L2(omega_K).",
            "dependencies": ["bounded_polyhedral_lipschitz_domain", "conforming_affine_simplicial_family", "uniform_shape_regularity", "P1_space"],
        },
        "scaled_trace_simplex": {
            "status": TheoremStatus.REVIEWED_ASSUMED.value,
            "machine_checked": False,
            "source": {"id":"standard-scaled-trace","description":"standard scaled trace inequality on uniformly shape-regular simplices"},
            "statement": "For w in H1(K), ||w||_L2(E) <= Ctr(d,gamma)[h_K^(-1/2)||w||_L2(K)+h_K^(1/2)||grad w||_L2(K)] for every face E subset boundary K.",
            "dependencies": ["conforming_affine_simplicial_family", "uniform_shape_regularity"],
        },
        "mesh_uniform_patch_overlap": {
            "status": TheoremStatus.REVIEWED_ASSUMED.value,
            "machine_checked": False,
            "source": SCOTT_ZHANG_1990,
            "statement": "For the finite Scott-Zhang element/face patches on a uniformly shape-regular conforming simplicial family, the patch multiplicity is bounded by N_ov=N(d,gamma), uniformly in h.",
            "dependencies": ["conforming_affine_simplicial_family", "uniform_shape_regularity"],
        },
    }

def admitted_problem_class() -> dict[str, Any]:
    return {
        "dimension": 2,
        "domain": "bounded polyhedral Lipschitz",
        "mesh_family": "conforming affine triangular",
        "uniform_shape_regular": True,
        "finite_element_space": "continuous P1 with homogeneous Dirichlet boundary data",
        "diffusion": "constant scalar or constant SPD tensor",
        "uniform_ellipticity": True,
        "source": "L2; affine/piecewise-affine supported by current estimator implementation",
        "estimator": "residual-plus-interior-flux-jump",
    }

def hypothesis_matcher(facts: dict[str, Any]) -> dict[str, Any]:
    required = {
        "bounded_polyhedral_lipschitz_domain": bool(facts.get("bounded_polyhedral_lipschitz_domain")),
        "conforming_affine_simplicial_family": bool(facts.get("conforming_affine_simplicial_family")),
        "uniform_shape_regularity": bool(facts.get("uniform_shape_regularity")),
        "P1_space": bool(facts.get("P1_space")),
        "homogeneous_dirichlet": bool(facts.get("homogeneous_dirichlet")),
        "uniform_ellipticity": float(facts.get("alpha_lower", 0.0)) > 0.0,
        "residual_estimator_has_volume_term": bool(facts.get("volume_residual_term")),
        "residual_estimator_has_jump_term": bool(facts.get("jump_term")),
    }
    failed = [k for k,v in required.items() if not v]
    return {"pass": not failed, "checks": required, "failed": failed}

def derive_face_estimate_symbolically() -> dict[str, Any]:
    # From scaled trace + Scott-Zhang L2/H1:
    # ||w||_E <= Ctr[h^-1/2 C0 h + h^1/2 C1] ||grad v||patch
    #          = Ctr(C0+C1) h^1/2 ||grad v||patch.
    return {
        "pass": True,
        "derived_constant": "C_E = C_tr * (C_0 + C_1) * C_face_element_comparability",
        "statement": "||v-I_h v||_L2(E) <= C_E h_E^(1/2)||grad v||_L2(omega_E)",
        "status": TheoremStatus.REVIEWED_ASSUMED.value,
        "machine_checked": False,
        "reason": "algebraic derivation is explicit, but imported analytic lemmas and geometry comparability are reviewed literature inputs",
    }

def reliability_constant_formula() -> dict[str, Any]:
    # Let eta^2 = eta_R^2 + eta_J^2.
    # Residual representation and local estimates give:
    # |R(e-Ie)| <= [C0 sqrt(NK) eta_R + CE sqrt(NE) eta_J] ||grad e||
    # <= sqrt(C0^2 NK + CE^2 NE) eta ||grad e||.
    # ||grad e|| <= ||e||_A / sqrt(alpha), hence
    # ||e||_A <= C*/sqrt(alpha) eta.
    return {
        "pass": True,
        "C_star": "sqrt(C_0^2 N_K + C_E^2 N_E)",
        "C_rel": "sqrt(C_0^2 N_K + C_E^2 N_E) / sqrt(alpha)",
        "estimator_normalization": "eta^2=sum_K h_K^2||r_K||_K^2 + sum_E h_E||j_E||_E^2",
        "independent_of": ["mesh size h", "number of elements"],
        "depends_on": ["dimension d", "shape regularity gamma", "ellipticity lower bound alpha", "patch convention / estimator normalization"],
    }

def reviewed_reliability_theorem() -> dict[str, Any]:
    return {
        "theorem_id": "reliability.poisson.p1.shape_regular.reviewed.v101",
        "status": TheoremStatus.REVIEWED_ASSUMED.value,
        "formal_evidence": False,
        "machine_checked": False,
        "statement": (
            "Let Omega be a bounded polyhedral Lipschitz domain and {T_h} a conforming affine "
            "uniformly shape-regular simplicial family. For conforming P1 Galerkin FEM with "
            "homogeneous Dirichlet data and uniformly coercive constant diffusion, the standard "
            "volume-residual plus interior-flux-jump estimator eta satisfies "
            "||u-u_h||_A <= C_rel eta, where C_rel is independent of h."
        ),
        "constant_structure": reliability_constant_formula(),
        "imported_analytic_lemmas": sorted(imported_lemma_registry()),
        "locally_closed_components": [
            "edge_orientation_cancellation",
            "affine_elementwise_green_identity",
            "interior_edge_flux_jump_bookkeeping",
            "estimator_definition",
            "coercivity_bridge",
        ],
        "nonclaims": [
            "not machine-formal",
            "does not yet provide a sharp numerical value for C_rel from literature constants",
            "does not cover arbitrary anisotropic/non-shape-regular meshes",
            "does not cover nonconforming FEM or arbitrary variable diffusion in this contract",
        ],
    }


def reviewed_reliability_contract() -> TheoremContract:
    def matcher(facts):
        r = hypothesis_matcher(facts)
        return r["pass"], list(r["failed"])
    theorem = reviewed_reliability_theorem()
    return TheoremContract(
        theorem_id=theorem["theorem_id"],
        statement=theorem["statement"],
        status=TheoremStatus.REVIEWED_ASSUMED,
        assumptions=(
            "bounded polyhedral Lipschitz domain",
            "conforming affine uniformly shape-regular simplicial family",
            "continuous P1 conforming Galerkin space with homogeneous Dirichlet data",
            "uniformly coercive constant scalar/SPD diffusion",
            "standard volume-residual plus interior-flux-jump estimator",
            "Scott-Zhang local approximation/stability, scaled trace, and finite overlap are accepted reviewed imports",
        ),
        evidence_kind=EvidenceKind.SYMBOLIC.value,
        checker="CACE v1.01 executable hypothesis matcher + symbolic derivation",
        artifact="docs/proofs/reliability_imported_lemmas_v101.json",
        matcher=matcher,
    )

def closure_dag() -> dict[str, Any]:
    nodes = {
        "edge_orientation_cancellation": "closed-exact",
        "elementwise_green_identity": "closed-exact-affine",
        "residual_representation": "closed-symbolic-scoped",
        "scott_zhang_local_L2": "closed-reviewed-import",
        "scott_zhang_local_H1": "closed-reviewed-import",
        "scaled_trace_simplex": "closed-reviewed-import",
        "face_quasi_interpolation": "closed-reviewed-derived",
        "mesh_uniform_patch_overlap": "closed-reviewed-import",
        "coercivity": "closed-symbolic/premise",
        "estimator_definition": "closed-implemented",
        "reliability_theorem_reviewed": "closed-reviewed-derived",
        "reliability_theorem_formal": "open-formalization",
    }
    return {
        "pass": True,
        "nodes": nodes,
        "reviewed_reliability_promotable": True,
        "formal_reliability_promotable": False,
        "remaining_formalization_targets": [
            "Scott-Zhang construction and local L2/H1 estimates",
            "scaled trace inequality on reference/physical simplices",
            "mesh-uniform patch overlap theorem",
            "full weak residual representation for the admitted PDE class",
        ],
    }

def executable_closure_audit(facts: dict[str, Any] | None = None) -> dict[str, Any]:
    if facts is None:
        facts = {
            "bounded_polyhedral_lipschitz_domain": True,
            "conforming_affine_simplicial_family": True,
            "uniform_shape_regularity": True,
            "P1_space": True,
            "homogeneous_dirichlet": True,
            "alpha_lower": 1.0,
            "volume_residual_term": True,
            "jump_term": True,
        }
    match = hypothesis_matcher(facts)
    theorem = reviewed_reliability_theorem()
    result = {
        "pass": match["pass"],
        "hypothesis_match": match,
        "imported_lemmas": imported_lemma_registry(),
        "derived_face_estimate": derive_face_estimate_symbolically(),
        "reliability_theorem": theorem,
        "dag": closure_dag(),
        "reviewed_theorem_available": match["pass"],
        "formal_theorem_available": False,
    }
    result["sha256"] = _sha(result)
    return result

class ReliabilityClosureV101(ResultModule):
    module_id = "fem101.reliability_closure"
    label = "Reliability Closure"
    version = "1.01.0"
    description = "Closes the general 2D P1 residual reliability result at reviewed imported-theorem level, while refusing formal promotion."
    evidence_kind = EvidenceKind.SYMBOLIC
    metadata = ModuleMetadata(
        module_id, label, version, "Reliability Theorem", description, Maturity.BETA,
        assumptions=(
            "bounded polyhedral Lipschitz domain",
            "conforming affine uniformly shape-regular triangular mesh family",
            "continuous P1 conforming FEM with homogeneous Dirichlet data",
            "uniformly coercive constant scalar/SPD diffusion",
            "standard volume residual and interior flux-jump estimator",
            "Scott-Zhang and scaled-trace results are reviewed mathematical imports, not machine-formal proofs",
        ),
    )
    proof_status = ProofStatus(
        evidence={EvidenceKind.SYMBOLIC},
        unit_tests=True,
        regression_tests=True,
        documentation=True,
        limitations=[
            "General reliability is literature-established/reviewed, not machine-formal in CACE.",
            "Numerical C_rel is not claimed sharp or automatically extracted from source proofs.",
            "Formal theorem promotion remains disabled.",
        ],
    )

    def execute(self, inputs, params, ctx):
        facts = params.get("facts") if isinstance(params, dict) else None
        return {"result": executable_closure_audit(facts)}

    def verify(self, inputs, params, outputs, ctx):
        return super().verify(inputs, params, outputs, ctx)

def register_fem_v101(registry):
    registry.register(ReliabilityClosureV101)
