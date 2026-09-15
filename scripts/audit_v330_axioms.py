#!/usr/bin/env python3
"""Fail closed unless all v3.30 endpoints have only allowed foundational axioms."""
from __future__ import annotations

import argparse
from pathlib import Path
import re

EXPECTED = [
    "smoothBoxProduct_hasFDerivAt",
    "smoothBoxProduct_divergence_eq_greenVolume",
    "smoothBoxGreen_schwartz",
    "boxGraphNormalTrace_smooth_eq_classical_auto",
    "submodule_topologicalClosure_eq_of_regularizer",
    "submodule_topologicalClosure_eq_ker_of_regularizer",
    "ker_le_topologicalClosure_of_regularizer",
    "topologicalClosure_eq_top_of_regularizer",
    "complexSmoothGraphClosure_eq_distributional_of_regularizer",
    "distributional_le_complexSmoothGraphClosure_of_regularizer",
    "realHDivSmoothGraphClosure_eq_distributionalPreimage_of_regularizer",
    "realDistributionalPreimage_le_HDivSmoothGraphClosure_of_regularizer",
    "mem_H1DistributionalGraphSubmodule_iff",
    "smoothComplexH1GraphMap_mem_distributional",
    "complexH1SmoothGraphClosure_le_distributional",
    "complexH1SmoothGraphClosure_eq_distributional_of_regularizer",
    "complexL2ToDistribution_l2RepresentativeOfInL2",
    "inH1GraphRepresentative_mem",
    "inHDivGraphRepresentative_mem",
    "inHDiv_iff_exists_distributionalGraphRepresentative",
    "besselRieszSymbol_norm_le",
    "h1RieszSymbol_norm_le_one",
    "h1RieszSymbol_hasTemperateGrowth",
    "besselPotential_neg_two_inH1_of_inL2",
    "besselPotential_neg_one_weakPartial_inH1_of_inL2",
    "rieszFiltered_weakPartial_inH1_of_inL2",
    "h1RieszCorrection_inH1",
    "inH1_of_besselRiesz_reconstruction",
]
ALLOWED = {"propext", "Classical.choice", "Quot.sound"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("audit", type=Path)
    args = parser.parse_args()
    text = args.audit.read_text(encoding="utf-8")
    if "sorryAx" in text:
        raise SystemExit("Rejected: theorem dependency contains sorryAx")

    found = re.findall(r"'([^']+)' depends on axioms: \[([^\]]*)\]", text)
    audited: dict[str, list[str]] = {}
    for theorem, payload in found:
        short = theorem.rsplit(".", 1)[-1]
        if short not in EXPECTED:
            continue
        axioms = {item.strip() for item in payload.split(",") if item.strip()}
        unexpected = axioms - ALLOWED
        if unexpected:
            raise SystemExit(
                f"Rejected: {theorem} depends on non-whitelisted axioms: {sorted(unexpected)}"
            )
        audited[short] = sorted(axioms)

    missing = sorted(set(EXPECTED) - set(audited))
    if missing:
        raise SystemExit(f"Rejected: missing theorem axiom reports: {missing}")
    print("Kernel axiom audit PASS:", audited)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
