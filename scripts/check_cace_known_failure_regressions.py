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
    ),
    "formal/cace_formal/CACEFormal/ReferenceSimplexNormalization.lean": (
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
        p1_match = NORMALIZER_P1_RE.search(normalization_text)
        if not p1_match:
            problems.append(
                f"{NORMALIZATION_SOURCE}: unable to locate normalizer_map_p1 regression block"
            )
        else:
            p1_body = p1_match.group("body")
            nf_bridge_pos = p1_body.find("have hden_nf")
            div_bridge_pos = p1_body.find("have hden_div")
            ring_nf_pos = p1_body.find("ring_nf")
            field_simp_pos = p1_body.find("field_simp [hden_div]")
            ring_pos = p1_body.find("ring", field_simp_pos + 1) if field_simp_pos >= 0 else -1
            if (
                nf_bridge_pos < 0
                or div_bridge_pos < 0
                or ring_nf_pos < 0
                or field_simp_pos < 0
                or ring_pos < 0
                or nf_bridge_pos > div_bridge_pos
                or div_bridge_pos > ring_nf_pos
                or ring_nf_pos > field_simp_pos
                or field_simp_pos > ring_pos
            ):
                problems.append(
                    f"{NORMALIZATION_SOURCE}: normalizer_map_p1 must prove both "
                    "canonical denominator bridges hden_nf and hden_div before "
                    "ring_nf, clear the exact denominator with field_simp [hden_div], "
                    "and finish only the polynomial remainder with ring"
                )

        linear_start = normalization_text.find("theorem normalizer_linearDet")
        linear_end = normalization_text.find(
            "/-- Nondegenerate triangles produce nonsingular normalizers. -/"
        )
        if linear_start >= 0 and linear_end > linear_start:
            linear_body = normalization_text[linear_start:linear_end]
            if re.search(r"field_simp\s*\[hT\]\s*\n\s*ring\b", linear_body):
                problems.append(
                    f"{NORMALIZATION_SOURCE}: normalizer_linearDet contains the "
                    "known closed-goal field_simp/ring tail"
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
            "normalization_tactic_order_guard": NORMALIZATION_SOURCE,
            "reserved_rcases_scan_root": str(formal_root.relative_to(ROOT)),
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
