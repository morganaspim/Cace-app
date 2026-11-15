#!/usr/bin/env python3
"""Dependency-free checks for known CACE proof failure regressions.

This script intentionally checks only failure classes that can be rejected
without invoking Lean.  It is safe to run in cheap hosted CI and before OCI
cache/toolchain setup.
"""
from __future__ import annotations

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_NONCOMPUTABLE = {
    "formal/cace_formal/CACEFormal/Piola.lean": (
        "noncomputable def piolaVector",
    ),
    "formal/cace_formal/CACEFormal/DualBladePiola.lean": (
        "noncomputable def piolaSequence",
    ),
    "formal/cace_formal/CACEFormal/AffineP1RT0Transport.lean": (
        "noncomputable def piolaRT0",
        "noncomputable def pullP1",
        "noncomputable def transportRT0SourceToTarget",
        "noncomputable def transportP1SourceToTarget",
    ),
    "formal/cace_formal/CACEFormal/ReferenceSimplexNormalization.lean": (
        "noncomputable def inverseEdgeLinear",
        "noncomputable def normalizer",
        "noncomputable def certifiedNondegenerate",
        "noncomputable def certifiedPositive",
    ),
    "formal/cace_formal/CACEFormal/PhysicalP1RT0Element.lean": (
        "noncomputable def cellPairing",
        "noncomputable def cellDivergence",
    ),
}

RCASES_RESERVED = {
    "by", "fun", "match", "let", "where", "do", "if", "then", "else", "in", "end"
}
RCASES_RE = re.compile(r"\brcases\b.*?\bwith\b.*?⟨(?P<body>[^⟩]*)⟩")
TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_']*")

NORMALIZATION_SOURCE = (
    "formal/cace_formal/CACEFormal/ReferenceSimplexNormalization.lean"
)
NORMALIZER_P1_RE = re.compile(
    r"theorem\s+normalizer_map_p1\b(?P<body>[\s\S]*?)(?=\n/-- The third vertex)"
)
INVERSE_EDGE_E1_RE = re.compile(
    r"theorem\s+inverseEdgeLinear_map_e1\b(?P<body>[\s\S]*?)(?=\n/-- The inverse-edge linear map sends the second)"
)
INVERSE_EDGE_E2_RE = re.compile(
    r"theorem\s+inverseEdgeLinear_map_e2\b(?P<body>[\s\S]*?)(?=\n@\[simp\] theorem inverseEdgeLinear_map_zero)"
)
MESH_ELEMENT_SOURCE = "formal/cace_formal/CACEFormal/MeshElementGeometry.lean"
EXECUTABLE_RATIONAL_SOURCE = (
    "formal/cace_formal/CACEFormal/ExecutableRationalGeometry.lean"
)
SOURCE_SANITY_WORKFLOW = ".github/workflows/cace-lean-source-sanity.yml"
POSITIVE_LAPLACIAN_SOURCE = "formal/cace_formal/CACEFormal/PositiveLaplacianAnnihilator.lean"
HDIV_ANNIHILATOR_SOURCE = "formal/cace_formal/CACEFormal/HDivGraphAnnihilator.lean"
RP2_CHAIN_SOURCE = "formal/cace_formal/CACEFormal/RP2ChainComplex.lean"
RECENTER_TO_REAL_RE = re.compile(
    r"theorem\s+recenterMap_toReal\b(?P<body>[\s\S]*?)(?=\n@\[simp\] theorem inverseEdgeLinear_toReal)"
)


def main() -> int:
    problems: list[str] = []

    for relative, declarations in REQUIRED_NONCOMPUTABLE.items():
        path = ROOT / relative
        if not path.is_file():
            problems.append(f"missing regression source: {relative}")
            continue
        text = path.read_text(encoding="utf-8")
        for declaration in declarations:
            if declaration not in text:
                problems.append(f"{relative}: missing required declaration '{declaration}'")

    normalization_path = ROOT / NORMALIZATION_SOURCE
    if not normalization_path.is_file():
        problems.append(f"missing regression source: {NORMALIZATION_SOURCE}")
    else:
        normalization_text = normalization_path.read_text(encoding="utf-8")
        required_normalization_symbols = (
            "def edge01",
            "def edge02",
            "def edgeDet",
            "noncomputable def inverseEdgeLinear",
            "theorem inverseEdgeLinear_map_e1",
            "theorem inverseEdgeLinear_map_e2",
            "theorem inverseEdgeLinear_linearDet",
        )
        for symbol in required_normalization_symbols:
            if symbol not in normalization_text:
                problems.append(
                    f"{NORMALIZATION_SOURCE}: missing structural normalization seam '{symbol}'"
                )

        p1_match = NORMALIZER_P1_RE.search(normalization_text)
        if not p1_match:
            problems.append(
                f"{NORMALIZATION_SOURCE}: unable to locate normalizer_map_p1 regression block"
            )
        else:
            p1_body = p1_match.group("body")
            if "inverseEdgeLinear_map_e1" not in p1_body:
                problems.append(
                    f"{NORMALIZATION_SOURCE}: normalizer_map_p1 must delegate to "
                    "inverseEdgeLinear_map_e1 instead of reopening denominator algebra"
                )
            for forbidden in ("have hden", "ring_nf", "field_simp"):
                if forbidden in p1_body:
                    problems.append(
                        f"{NORMALIZATION_SOURCE}: normalizer_map_p1 reintroduced "
                        f"fragile denominator tactic seam {forbidden!r}"
                    )

        for label, pattern in (
            ("inverseEdgeLinear_map_e1", INVERSE_EDGE_E1_RE),
            ("inverseEdgeLinear_map_e2", INVERSE_EDGE_E2_RE),
        ):
            match = pattern.search(normalization_text)
            if not match:
                problems.append(
                    f"{NORMALIZATION_SOURCE}: unable to locate {label} regression block"
                )
                continue
            body = match.group("body")
            if "have hΔcomm" not in body or "field_simp [hΔ, hΔcomm]" not in body:
                problems.append(
                    f"{NORMALIZATION_SOURCE}: {label} must establish the canonical "
                    "hΔcomm nonzero bridge before field_simp"
                )

        linear_start = normalization_text.find("theorem normalizer_linearDet")
        linear_end = normalization_text.find(
            "/-- Nondegenerate triangles produce nonsingular normalizers. -/"
        )
        if linear_start >= 0 and linear_end > linear_start:
            linear_body = normalization_text[linear_start:linear_end]
            if "inverseEdgeLinear_linearDet" not in linear_body:
                problems.append(
                    f"{NORMALIZATION_SOURCE}: normalizer_linearDet must reuse "
                    "inverseEdgeLinear_linearDet"
                )
            if "field_simp" in linear_body:
                problems.append(
                    f"{NORMALIZATION_SOURCE}: normalizer_linearDet must not reopen "
                    "raw denominator simplification after inverse-edge factoring"
                )

    mesh_path = ROOT / MESH_ELEMENT_SOURCE
    if not mesh_path.is_file():
        problems.append(f"missing regression source: {MESH_ELEMENT_SOURCE}")
    else:
        mesh_text = mesh_path.read_text(encoding="utf-8")
        det_start = mesh_text.find("theorem realTriangle_det")
        det_end = mesh_text.find(
            "/-- Every canonical element triangle produced from a mesh certificate"
        )
        if det_start < 0 or det_end <= det_start:
            problems.append(
                f"{MESH_ELEMENT_SOURCE}: unable to locate realTriangle_det regression block"
            )
        else:
            det_body = mesh_text[det_start:det_end]
            required = "simp only [realTriangle, realPoint, Triangle2.det]"
            if required not in det_body or "exact_mod_cast" not in det_body:
                problems.append(
                    f"{MESH_ELEMENT_SOURCE}: realTriangle_det must simplify structure "
                    "projections before exact_mod_cast"
                )
            if "unfold realTriangle realPoint Triangle2.det" in det_body:
                problems.append(
                    f"{MESH_ELEMENT_SOURCE}: realTriangle_det reintroduced the known "
                    "raw-unfold mod_cast failure seam"
                )

    executable_path = ROOT / EXECUTABLE_RATIONAL_SOURCE
    if not executable_path.is_file():
        problems.append(f"missing regression source: {EXECUTABLE_RATIONAL_SOURCE}")
    else:
        executable_text = executable_path.read_text(encoding="utf-8")
        match = RECENTER_TO_REAL_RE.search(executable_text)
        if not match:
            problems.append(
                f"{EXECUTABLE_RATIONAL_SOURCE}: unable to locate recenterMap_toReal regression block"
            )
        else:
            body = match.group("body")
            if "Point.toReal" not in body:
                problems.append(
                    f"{EXECUTABLE_RATIONAL_SOURCE}: recenterMap_toReal must explicitly "
                    "normalize Point.toReal before closing rational-to-real negation casts"
                )

    positive_laplacian_path = ROOT / POSITIVE_LAPLACIAN_SOURCE
    if not positive_laplacian_path.is_file():
        problems.append(f"missing regression source: {POSITIVE_LAPLACIAN_SOURCE}")
    else:
        positive_laplacian_text = positive_laplacian_path.read_text(encoding="utf-8")
        start = positive_laplacian_text.find(
            "theorem positiveLaplacianLowSymbol_hasTemperateGrowth"
        )
        end = positive_laplacian_text.find(
            "theorem positiveLaplacianEnergySymbol_hasTemperateGrowth"
        )
        if start < 0 or end <= start:
            problems.append(
                f"{POSITIVE_LAPLACIAN_SOURCE}: unable to locate low-symbol growth theorem block"
            )
        else:
            body = positive_laplacian_text[start:end]
            if "hasTemperateGrowth_one_add_norm_sq_rpow" not in body:
                problems.append(
                    f"{POSITIVE_LAPLACIAN_SOURCE}: "
                    "positiveLaplacianLowSymbol_hasTemperateGrowth must reuse Mathlib "
                    "Bessel-potential temperate-growth theorem"
                )
            if "fun_prop" in body:
                problems.append(
                    f"{POSITIVE_LAPLACIAN_SOURCE}: low-symbol reciprocal growth must not "
                    "delegate to fun_prop"
                )
            if "Function.Complex.hasTemperateGrowth_ofReal.comp" in body:
                problems.append(
                    f"{POSITIVE_LAPLACIAN_SOURCE}: parenthesize "
                    "Complex.hasTemperateGrowth_ofReal before composing the theorem"
                )
            if "(Function.Complex.hasTemperateGrowth_ofReal).comp" not in body:
                problems.append(
                    f"{POSITIVE_LAPLACIAN_SOURCE}: low-symbol complex lift must compose "
                    "the pinned Complex.hasTemperateGrowth_ofReal theorem explicitly"
                )

        low_lap_start = positive_laplacian_text.find(
            "theorem positiveLaplacianLow_laplacian"
        )
        low_lap_end = positive_laplacian_text.find(
            "theorem laplacian_eq_self_imp_eq_zero"
        )
        if low_lap_start < 0 or low_lap_end <= low_lap_start:
            problems.append(
                f"{POSITIVE_LAPLACIAN_SOURCE}: unable to locate low-Laplacian multiplier block"
            )
        else:
            low_lap_body = positive_laplacian_text[low_lap_start:low_lap_end]
            if "ContinuousLinearMap.map_smul_of_tower" not in low_lap_body:
                problems.append(
                    f"{POSITIVE_LAPLACIAN_SOURCE}: low-Laplacian proof must preserve "
                    "the real-to-complex scalar tower explicitly"
                )
            if "Complex.coe_smul" not in low_lap_body:
                problems.append(
                    f"{POSITIVE_LAPLACIAN_SOURCE}: low-Laplacian proof must normalize "
                    "real scalar action through Complex.coe_smul"
                )
            if "rw [map_smul]" in low_lap_body:
                problems.append(
                    f"{POSITIVE_LAPLACIAN_SOURCE}: low-Laplacian proof reintroduced the "
                    "invalid plain map_smul scalar-tower seam"
                )

        if "Complex.ofReal ((2 * Real.pi) ^ 2)" not in positive_laplacian_text:
            problems.append(
                f"{POSITIVE_LAPLACIAN_SOURCE}: positive-frequency coefficient must use "
                "one canonical Complex.ofReal ((2 * Real.pi) ^ 2) representation"
            )

    hdiv_annihilator_path = ROOT / HDIV_ANNIHILATOR_SOURCE
    if not hdiv_annihilator_path.is_file():
        problems.append(f"missing regression source: {HDIV_ANNIHILATOR_SOURCE}")
    else:
        hdiv_annihilator_text = hdiv_annihilator_path.read_text(encoding="utf-8")
        start = hdiv_annihilator_text.find(
            "theorem hdivGraph_eq_zero_of_reversedH1"
        )
        if start < 0:
            problems.append(
                f"{HDIV_ANNIHILATOR_SOURCE}: unable to locate reversed-H1 zero theorem"
            )
        else:
            body = hdiv_annihilator_text[start:]
            if "complexL2ToDistribution_injective n hgDist" in body:
                problems.append(
                    f"{HDIV_ANNIHILATOR_SOURCE}: injectivity must normalize literal zero "
                    "to complexL2ToDistribution n 0 before application"
                )
            if "simpa using hgDist" not in body:
                problems.append(
                    f"{HDIV_ANNIHILATOR_SOURCE}: reversed-H1 zero proof must explicitly "
                    "normalize the distributional zero equality before injectivity"
                )

    # F-035: keep Fintype-to-Finset sum normalization explicit in the
    # quarantined RP2 linearity proofs, and use arbitrary-chain LinearMap.ext.
    rp2_path = ROOT / RP2_CHAIN_SOURCE
    if not rp2_path.is_file():
        problems.append(f"missing regression source: {RP2_CHAIN_SOURCE}")
    else:
        rp2_text = rp2_path.read_text(encoding="utf-8")
        for label, start_token, end_token, expected in (
            (
                "boundary1Linear.map_smul'",
                "def boundary1Linear",
                "/-- The second integral boundary",
                "change (∑ e ∈ (Finset.univ : Finset Edge),",
            ),
            (
                "boundary2Linear.map_smul'",
                "def boundary2Linear",
                "/-- The two linear boundary maps",
                "change (∑ f ∈ (Finset.univ : Finset Facet),",
            ),
        ):
            start = rp2_text.find(start_token)
            end = rp2_text.find(end_token, start + len(start_token)) if start >= 0 else -1
            if start < 0 or end <= start:
                problems.append(f"{RP2_CHAIN_SOURCE}: unable to locate {label} regression block")
                continue
            body = rp2_text[start:end]
            if (
                expected not in body
                or "simp_rw [mul_assoc]" not in body
                or "rw [← Finset.mul_sum]" not in body
                or "sorry" in body
            ):
                problems.append(
                    f"{RP2_CHAIN_SOURCE}: {label} must normalize product association, "
                    "convert the Fintype sum to Finset.univ, factor the scalar, and contain no sorry"
                )
        comp_start = rp2_text.find("theorem boundaryLinear_comp_zero")
        comp_end = rp2_text.find("/-- Integral 1-cycles", comp_start) if comp_start >= 0 else -1
        if comp_start < 0 or comp_end <= comp_start:
            problems.append(f"{RP2_CHAIN_SOURCE}: unable to locate boundaryLinear_comp_zero")
        else:
            comp_body = rp2_text[comp_start:comp_end]
            if (
                "apply LinearMap.ext" not in comp_body
                or "boundary_squared_zero z" not in comp_body
                or "sorry" in comp_body
            ):
                problems.append(
                    f"{RP2_CHAIN_SOURCE}: chain-map composition must use extensionality "
                    "over an arbitrary 2-chain and contain no sorry"
                )
        if "CACEFormal.RP2ChainComplex" not in (ROOT / "formal/cace_formal/proof_guardrails.json").read_text(encoding="utf-8"):
            problems.append("RP2 chain complex must remain quarantined from the audited root")

    # F-036: independent CACE workflows need distinct concurrency groups.
    # GitHub retains only one pending run per group; a shared group can silently
    # replace the exact-pin preflight with source-sanity/collaboration runs.
    workflow_group_paths = {
        "exact-pin": ROOT / ".github/workflows/cace-exact-pin-lean-preflight.yml",
        "source-sanity": ROOT / ".github/workflows/cace-lean-source-sanity.yml",
        "collaboration": ROOT / ".github/workflows/cace-collaboration-validation.yml",
    }
    observed_groups: dict[str, str] = {}
    for label, workflow_path in workflow_group_paths.items():
        if not workflow_path.is_file():
            problems.append(f"missing CACE workflow for concurrency guard: {workflow_path}")
            continue
        workflow_text = workflow_path.read_text(encoding="utf-8")
        group_match = re.search(r"(?m)^  group:\s*([^\s#]+)\s*$", workflow_text)
        if group_match is None:
            problems.append(f"{workflow_path}: missing dedicated concurrency group")
            continue
        group = group_match.group(1)
        if group in observed_groups:
            problems.append(
                f"{workflow_path}: concurrency group collides with {observed_groups[group]}"
            )
        observed_groups[group] = label
        if re.search(r"(?m)^  cancel-in-progress:\s*false\s*$", workflow_text) is None:
            problems.append(f"{workflow_path}: cancel-in-progress must remain false")

    source_sanity_path = ROOT / SOURCE_SANITY_WORKFLOW
    if not source_sanity_path.is_file():
        problems.append(f"missing regression source: {SOURCE_SANITY_WORKFLOW}")
    else:
        source_sanity_text = source_sanity_path.read_text(encoding="utf-8")
        required_ref = "ref: ${{ github.event.pull_request.head.sha || github.sha }}"
        if required_ref not in source_sanity_text:
            problems.append(
                f"{SOURCE_SANITY_WORKFLOW}: checkout must fall back to github.sha on push events"
            )

    formal_root = ROOT / "formal" / "cace_formal" / "CACEFormal"
    for path in sorted(formal_root.rglob("*.lean")):
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            match = RCASES_RE.search(line)
            if not match:
                continue
            for token in TOKEN_RE.findall(match.group("body")):
                if token in RCASES_RESERVED:
                    problems.append(
                        f"{path.relative_to(ROOT)}:{lineno}: reserved rcases identifier {token!r}"
                    )

    if problems:
        print("CACE_KNOWN_FAILURE_REGRESSIONS_REJECTED")
        for problem in problems:
            print(f"- {problem}")
        return 1

    print(
        "CACE_KNOWN_FAILURE_REGRESSIONS_OK",
        {
            "noncomputable_files": len(REQUIRED_NONCOMPUTABLE),
            "normalization_structural_guard": NORMALIZATION_SOURCE,
            "reserved_rcases_scan_root": str(formal_root.relative_to(ROOT)),
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
