from __future__ import annotations

from hashlib import sha256
from pathlib import Path

ROOT = Path("formal/cace_formal/CACEFormal")

FAILURE_FINGERPRINTS = (
    "CACE-LEAN-NHDS-001",
    "CACE-LEAN-SMOOTH-CONGR-001",
    "CACE-LEAN-COMPLEX-KERNEL-INFERENCE-001",
)


def replace_exact(path: Path, old: str, new: str, expected: int = 1) -> None:
    text = path.read_text(encoding="utf-8")
    found = text.count(old)
    if found != expected:
        raise SystemExit(
            f"{path}: failure fingerprint mismatch; expected {expected} occurrences, "
            f"found {found}: {old!r}"
        )
    path.write_text(text.replace(old, new), encoding="utf-8")


def record_hash(hashes: list[tuple[str, str, str]], path: Path, before: bytes) -> None:
    after = path.read_bytes()
    hashes.append((path.name, sha256(before).hexdigest(), sha256(after).hexdigest()))


def main() -> None:
    hashes: list[tuple[str, str, str]] = []

    # CACE-LEAN-NHDS-001
    # Use the explicit Filter function name already used by the generic regularization theorem.
    real_path = ROOT / "RealGraphRegularizationCriterion.lean"
    real_before = real_path.read_bytes()
    real_text = real_before.decode("utf-8")
    real_found = real_text.count("(𝓝 x)")
    if real_found != 2:
        raise SystemExit(
            f"{real_path}: CACE-LEAN-NHDS-001 mismatch; expected 2, found {real_found}"
        )
    real_path.write_text(real_text.replace("(𝓝 x)", "(nhds x)"), encoding="utf-8")
    record_hash(hashes, real_path, real_before)

    graph_path = ROOT / "GraphRegularizationCriterion.lean"
    graph_before = graph_path.read_bytes()
    graph_text = graph_before.decode("utf-8")
    graph_found = graph_text.count("(𝓝 x)")
    if graph_found != 2:
        raise SystemExit(
            f"{graph_path}: CACE-LEAN-NHDS-001 mismatch; expected 2, found {graph_found}"
        )
    graph_path.write_text(graph_text.replace("(𝓝 x)", "(nhds x)"), encoding="utf-8")

    # CACE-LEAN-COMPLEX-KERNEL-INFERENCE-001
    # Avoid the expensive kernel-definitional elaboration path.  The target relation already has a
    # proved closedness theorem, so use the same generic closed-target regularization principle that
    # compiles for the real wrapper.  This changes proof search, not the theorem statement.
    old_eq = """  change (ComplexHDivSmoothGraphCore n).topologicalClosure =
    (complexHDivGraphDefect n).ker
  exact submodule_topologicalClosure_eq_ker_of_regularizer
    (ComplexHDivSmoothGraphCore n) (complexHDivGraphDefect n)
    (ComplexHDivSmoothGraphCore_le_distributional n)
    R hcore htendsto
"""
    new_eq = """  exact submodule_topologicalClosure_eq_of_regularizer
    (ComplexHDivSmoothGraphCore n) (HDivDistributionalGraphSubmodule n)
    (ComplexHDivSmoothGraphCore_le_distributional n)
    (isClosed_HDivDistributionalGraphSubmodule n)
    R hcore htendsto
"""
    replace_exact(graph_path, old_eq, new_eq)

    old_le = """  change (complexHDivGraphDefect n).ker ≤
    (ComplexHDivSmoothGraphCore n).topologicalClosure
  exact ker_le_topologicalClosure_of_regularizer
    (ComplexHDivSmoothGraphCore n) (complexHDivGraphDefect n)
    (ComplexHDivSmoothGraphCore_le_distributional n)
    R hcore htendsto
"""
    new_le = """  exact submodule_le_topologicalClosure_of_regularizer
    (ComplexHDivSmoothGraphCore n) (HDivDistributionalGraphSubmodule n)
    (ComplexHDivSmoothGraphCore_le_distributional n)
    (isClosed_HDivDistributionalGraphSubmodule n)
    R hcore htendsto
"""
    replace_exact(graph_path, old_le, new_le)
    record_hash(hashes, graph_path, graph_before)

    # CACE-LEAN-SMOOTH-CONGR-001
    # Replace fragile definitional/simp normalization with explicit derivative and integrability
    # congruence bridges.  This candidate already compiled successfully in isolation.
    path = ROOT / "SmoothBoxGreenAuto.lean"
    before = path.read_bytes()

    replace_exact(
        path,
        "import CACEFormal.BoxClassicalAgreement\nimport Mathlib.Analysis.Calculus.FDeriv.Mul\n",
        "import CACEFormal.BoxClassicalAgreement\nimport Mathlib.Analysis.Calculus.FDeriv.Congr\nimport Mathlib.Analysis.Calculus.FDeriv.Mul\n",
    )
    replace_exact(
        path,
        "open Set Finset MeasureTheory\n",
        "open Set Finset MeasureTheory Filter\n",
    )
    replace_exact(
        path,
        "    v x • fderiv ℝ (q i) x + q i x • fderiv ℝ v x\n",
        "    v x • fderiv ℝ (q i) x + (fderiv ℝ v x).smulRight (q i x)\n",
    )

    old_deriv = """  simpa only [smoothBoxProductFDeriv, scalarTimesVector, smoothBoxVectorFunction] using
    (hasFDerivAt_pi.2 fun i => (v.hasFDerivAt x).mul ((q i).hasFDerivAt x))
"""
    new_deriv = """  apply hasFDerivAt_pi'.2
  intro i
  have hq :
      HasFDerivAt (q i : BoxPoint n → ℝ) (fderiv ℝ (q i) x) x := by
    exact (q i).hasFDerivAt x
  have hprod :
      HasFDerivAt
        ((v : BoxPoint n → ℝ) * (q i : BoxPoint n → ℝ))
        (v x • fderiv ℝ (q i) x + (fderiv ℝ v x).smulRight (q i x)) x :=
    (v.hasFDerivAt x).smul hq
  have hfun :
      (fun y : BoxPoint n => v y * (q i) y) =ᶠ[nhds x]
        ((v : BoxPoint n → ℝ) * (q i : BoxPoint n → ℝ)) := by
    filter_upwards [] with y
    rfl
  have htarget := hfun.hasFDerivAt_iff.mpr hprod
  simpa only [smoothBoxProductFDeriv, scalarTimesVector, smoothBoxVectorFunction,
    ContinuousLinearMap.proj_pi] using htarget
"""
    replace_exact(path, old_deriv, new_deriv)
    replace_exact(
        path,
        "        boxBasisVector]\n",
        "        boxBasisVector, mul_comm]\n",
    )

    old_integrable = """  have hgreen :
      IntegrableOn
        (smoothGreenVolumeTerm (smoothBoxVectorFunction q) v
          (smoothBoxGradientFunction v) (smoothBoxDivergence q))
        (Icc a b) := by
    simpa [smoothGreenVolumeTerm, smoothBoxVectorFunction, smoothBoxGradientFunction] using
      hsum.add hdiv
  simpa only [smoothBoxProduct_divergence_eq_greenVolume] using hgreen
"""
    new_integrable = """  exact (hsum.add hdiv).congr_fun
    (fun x hx => by
      simpa [smoothGreenVolumeTerm, smoothBoxVectorFunction, smoothBoxGradientFunction] using
        (smoothBoxProduct_divergence_eq_greenVolume q v x).symm)
    measurableSet_Icc
"""
    replace_exact(path, old_integrable, new_integrable)

    record_hash(hashes, path, before)

    Path("continuum-isolation-fingerprints.txt").write_text(
        "\n".join(FAILURE_FINGERPRINTS) + "\n", encoding="utf-8"
    )
    out = Path("continuum-isolation-hashes.txt")
    out.write_text(
        "".join(
            f"{name} original_sha256={old} patched_sha256={new}\n"
            for name, old, new in hashes
        ),
        encoding="utf-8",
    )
    print(Path("continuum-isolation-fingerprints.txt").read_text(encoding="utf-8"), end="")
    print(out.read_text(encoding="utf-8"), end="")


if __name__ == "__main__":
    main()
