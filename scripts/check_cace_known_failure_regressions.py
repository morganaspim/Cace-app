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
