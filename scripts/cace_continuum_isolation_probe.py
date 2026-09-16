from __future__ import annotations

from hashlib import sha256
from pathlib import Path

ROOT = Path("formal/cace_formal/CACEFormal")


def replace_exact(path: Path, old: str, new: str, expected: int = 1) -> None:
    text = path.read_text(encoding="utf-8")
    found = text.count(old)
    if found != expected:
        raise SystemExit(
            f"{path}: expected {expected} occurrences, found {found}: {old!r}"
        )
    path.write_text(text.replace(old, new), encoding="utf-8")


def main() -> None:
    hashes: list[tuple[str, str, str]] = []

    for name in (
        "GraphRegularizationCriterion.lean",
        "RealGraphRegularizationCriterion.lean",
    ):
        path = ROOT / name
        before = path.read_bytes()
        text = before.decode("utf-8")
        found = text.count("(𝓝 x)")
        if found != 2:
            raise SystemExit(
                f"{path}: expected 2 neighborhood-notation occurrences, found {found}"
            )
        path.write_text(text.replace("(𝓝 x)", "(nhds x)"), encoding="utf-8")
        after = path.read_bytes()
        hashes.append((name, sha256(before).hexdigest(), sha256(after).hexdigest()))

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

    after = path.read_bytes()
    hashes.append((path.name, sha256(before).hexdigest(), sha256(after).hexdigest()))

    out = Path("continuum-isolation-hashes.txt")
    out.write_text(
        "".join(
            f"{name} original_sha256={old} patched_sha256={new}\n"
            for name, old, new in hashes
        ),
        encoding="utf-8",
    )
    print(out.read_text(encoding="utf-8"), end="")


if __name__ == "__main__":
    main()
