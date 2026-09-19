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
            "reserved_rcases_scan_root": str(formal_root.relative_to(ROOT)),
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
