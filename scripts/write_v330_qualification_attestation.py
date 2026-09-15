#!/usr/bin/env python3
"""Write the canonical v3.30 qualification attestation after all checks pass.

This script does not run Lean and cannot create proof evidence on its own. It is
called only after the pinned build, unfinished-token guard, and kernel axiom
audit have succeeded. The resulting digest is provenance for that successful
qualification run; it does not broaden the theorem statements or remove their
hypotheses.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess

CLAIM_ID = "cace.v330.continuum-proof-strengthening"
MATHLIB_COMMIT = "520045ab14e26149ee970e2e617ca04b09bde5d6"
AUDITED_SOURCE_FILES = [
    "CACEFormal/SmoothBoxGreenAuto.lean",
    "CACEFormal/RegularizationClosure.lean",
    "CACEFormal/GraphRegularizationCriterion.lean",
    "CACEFormal/RealGraphRegularizationCriterion.lean",
    "CACEFormal/H1DomainBridge.lean",
    "CACEFormal/H1BesselRieszReduction.lean",
    "CACEFormal/DistributionalGraphRepresentatives.lean",
    "CACEFormal/V330AxiomAudit.lean",
]
THEOREMS = [
    "CACEFormal.Continuum.smoothBoxProduct_hasFDerivAt",
    "CACEFormal.Continuum.smoothBoxProduct_divergence_eq_greenVolume",
    "CACEFormal.Continuum.smoothBoxGreen_schwartz",
    "CACEFormal.Continuum.boxGraphNormalTrace_smooth_eq_classical_auto",
    "CACEFormal.Continuum.submodule_topologicalClosure_eq_ker_of_regularizer",
    "CACEFormal.Continuum.complexSmoothGraphClosure_eq_distributional_of_regularizer",
    "CACEFormal.Continuum.realHDivSmoothGraphClosure_eq_distributionalPreimage_of_regularizer",
    "CACEFormal.Continuum.complexH1SmoothGraphClosure_eq_distributional_of_regularizer",
    "CACEFormal.Continuum.inH1GraphRepresentative_mem",
    "CACEFormal.Continuum.inHDiv_iff_exists_distributionalGraphRepresentative",
    "CACEFormal.Continuum.h1RieszSymbol_norm_le_one",
    "CACEFormal.Continuum.rieszFiltered_weakPartial_inH1_of_inL2",
    "CACEFormal.Continuum.h1RieszCorrection_inH1",
    "CACEFormal.Continuum.inH1_of_besselRiesz_reconstruction",
]
NONCLAIMS = [
    "The v3.30 H1/H(div) regularization criteria do not themselves construct the unconditional regularizers required for reverse graph inclusion.",
    "The new H1 distributional graph relation is not yet identified with Mathlib Bessel-potential InH1 in the converse direction.",
    "CACE does not establish external reproducer/reviewer identity or independence; those remain external trust boundaries.",
]


def out(cmd: list[str], *, cwd: Path | None = None) -> str:
    return subprocess.check_output(cmd, cwd=cwd, text=True).strip()


def source_bundle_sha256(formal_dir: Path) -> str:
    digest = hashlib.sha256()
    for relative in AUDITED_SOURCE_FILES:
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update((formal_dir / relative).read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--formal-dir", type=Path, required=True)
    parser.add_argument("--qualification-system", required=True)
    parser.add_argument("--qualification-run-id", required=True)
    parser.add_argument("--workflow-run-id", type=int)
    parser.add_argument("--axiom-audit", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path.cwd())
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    formal_dir = args.formal_dir.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    if not args.qualification_system.strip() or not args.qualification_run_id.strip():
        raise SystemExit("qualification system/run id must be non-empty")
    if args.qualification_system == "github-actions" and (
        args.workflow_run_id is None or args.workflow_run_id <= 0
    ):
        raise SystemExit("github-actions attestation requires a positive workflow run id")
    if not args.axiom_audit.is_file():
        raise SystemExit(f"axiom audit is missing: {args.axiom_audit}")

    commit = out(["git", "rev-parse", "HEAD"], cwd=repo_root)
    if len(commit) != 40:
        raise SystemExit("could not resolve exact 40-hex git commit")
    if out(["git", "status", "--porcelain"], cwd=repo_root):
        raise SystemExit("refusing qualification attestation for a dirty working tree")

    mathlib_commit = out(
        ["git", "-C", str(formal_dir / ".lake/packages/mathlib"), "rev-parse", "HEAD"]
    )
    if mathlib_commit != MATHLIB_COMMIT:
        raise SystemExit(
            f"mathlib commit mismatch: expected {MATHLIB_COMMIT}, got {mathlib_commit}"
        )

    data = {
        "release": "3.30.0-dev",
        "claim_id": CLAIM_ID,
        "status": "PASS",
        "commit": commit,
        "qualification_system": args.qualification_system.strip(),
        "qualification_run_id": args.qualification_run_id.strip(),
        "workflow_run_id": args.workflow_run_id,
        "lean_version": out(["lean", "--version"]),
        "mathlib_commit": mathlib_commit,
        "build_target": "CACEFormal.V330AxiomAudit",
        "mathlib_cache_scope": "CACEFormal/V330AxiomAudit.lean transitive import closure",
        "audited_source_files": AUDITED_SOURCE_FILES,
        "audited_source_bundle_sha256": source_bundle_sha256(formal_dir),
        "axiom_audit_sha256": hashlib.sha256(args.axiom_audit.read_bytes()).hexdigest(),
        "scope": "Automatic smooth product calculus, generic kernel regularization-to-closure automation, H1/H(div) graph-density reductions, exact L2 graph representatives for distributional predicates, and framework-level artifact-bound claim promotion guards.",
        "theorems": THEOREMS,
        "promotion_guards": {
            "unfinished_tokens_rejected": True,
            "sorryAx_rejected": True,
            "nonfoundation_axioms_rejected": True,
            "allowed_foundational_axioms": ["propext", "Classical.choice", "Quot.sound"],
            "open_problem_requires_artifact_bound_independent_reproduction": True,
            "open_problem_requires_artifact_bound_external_review": True,
            "module_self_promotion_reserved_flags_rejected": True,
            "numerical_symbolic_interval_evidence_cannot_self_promote": True,
        },
        "nonclaims": NONCLAIMS,
    }

    path = output_dir / "v330_formal_qualification_attestation.json"
    rendered = json.dumps(data, indent=2, sort_keys=True) + "\n\n"
    path.write_text(rendered, encoding="utf-8")
    digest = hashlib.sha256(rendered.encode("utf-8")).hexdigest()
    (output_dir / "v330_formal_qualification_attestation.sha256").write_text(
        f"{digest}  {path.name}\n", encoding="utf-8"
    )
    print(rendered, end="")
    print("attestation_sha256:", digest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
