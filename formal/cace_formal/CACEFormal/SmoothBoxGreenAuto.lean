import CACEFormal.BoxClassicalAgreement
import Mathlib.Analysis.Calculus.FDeriv.Congr
import Mathlib.Analysis.Calculus.FDeriv.Mul
import Mathlib.Analysis.Calculus.FDeriv.Pi

namespace CACEFormal

open Set Finset MeasureTheory Filter
open scoped BigOperators LineDeriv SchwartzMap

namespace Continuum

noncomputable section

/-!
# v3.30 automatic smooth box calculus

The v3.29 classical-agreement theorem deliberately exposed the local product-rule derivative as an
explicit hypothesis. This file discharges that hypothesis for the actual Schwartz smooth core used
by the box graph spaces. The resulting endpoint theorem needs only the box ordering hypothesis and
smooth core fields: the Frechet derivative, product rule, continuity and integrability obligations
are constructed by Lean.
-/

/-- Frechet derivative of the smooth product field `x ↦ v x * q x`, coordinate by coordinate. -/
noncomputable def smoothBoxProductFDeriv {n : Nat}
    (q : BoxSmoothVector n) (v : BoxSmoothScalar n) (x : BoxPoint n) :
    BoxPoint n →L[ℝ] BoxPoint n :=
  ContinuousLinearMap.pi fun i =>
    v x • fderiv ℝ (q i) x + (fderiv ℝ v x).smulRight (q i x)

/-- The derivative used by the box divergence theorem is generated automatically from the
Schwartz smooth-core data by the Frechet product rule. -/
theorem smoothBoxProduct_hasFDerivAt {n : Nat}
    (q : BoxSmoothVector n) (v : BoxSmoothScalar n) (x : BoxPoint n) :
    HasFDerivAt (scalarTimesVector v (smoothBoxVectorFunction q))
      (smoothBoxProductFDeriv q v x) x := by
  apply hasFDerivAt_pi'.2
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
      (fun y : BoxPoint n => v y * (q i) y) =ᶠ[𝓝 x]
        ((v : BoxPoint n → ℝ) * (q i : BoxPoint n → ℝ)) := by
    filter_upwards [] with y
    rfl
  have htarget := hfun.hasFDerivAt_iff.mpr hprod
  simpa only [smoothBoxProductFDeriv, scalarTimesVector, smoothBoxVectorFunction,
    ContinuousLinearMap.proj_pi] using htarget

/-- Taking the coordinate trace of the automatically generated product derivative gives exactly
`q · ∇v + (div q) v`. This is the local calculus obligation that v3.29 left explicit. -/
theorem smoothBoxProduct_divergence_eq_greenVolume {n : Nat}
    (q : BoxSmoothVector n) (v : BoxSmoothScalar n) (x : BoxPoint n) :
    (∑ i : Fin (n + 1),
      smoothBoxProductFDeriv q v x (Pi.single i (1 : ℝ)) i) =
      smoothGreenVolumeTerm (smoothBoxVectorFunction q) v
        (smoothBoxGradientFunction v) (smoothBoxDivergence q) x := by
  classical
  calc
    (∑ i : Fin (n + 1),
        smoothBoxProductFDeriv q v x (Pi.single i (1 : ℝ)) i) =
      ∑ i : Fin (n + 1),
        (v x * (∂_{boxBasisVector i} (q i)) x +
          q i x * (∂_{boxBasisVector i} v) x) := by
      apply Finset.sum_congr rfl
      intro i hi
      simp [smoothBoxProductFDeriv, SchwartzMap.lineDerivOp_apply_eq_fderiv,
        boxBasisVector, mul_comm]
    _ = (∑ i : Fin (n + 1), q i x * (∂_{boxBasisVector i} v) x) +
        (∑ i : Fin (n + 1), (∂_{boxBasisVector i} (q i)) x) * v x := by
      rw [Finset.sum_add_distrib, ← Finset.mul_sum]
      ring
    _ = smoothGreenVolumeTerm (smoothBoxVectorFunction q) v
        (smoothBoxGradientFunction v) (smoothBoxDivergence q) x := by
      simp [smoothGreenVolumeTerm, smoothBoxVectorFunction, smoothBoxGradientFunction,
        smoothBoxDivergence]

/-- The automatically generated product field is continuous everywhere. -/
theorem smoothBoxProduct_continuous {n : Nat}
    (q : BoxSmoothVector n) (v : BoxSmoothScalar n) :
    Continuous (scalarTimesVector v (smoothBoxVectorFunction q)) := by
  apply continuous_pi
  intro i
  exact v.continuous.mul (q i).continuous

/-- The divergence integrand produced by the automatic derivative is integrable on every closed
box because it is pointwise the smooth Green volume term. -/
theorem smoothBoxProduct_divergence_integrableOn {n : Nat}
    (a b : BoxPoint n) (q : BoxSmoothVector n) (v : BoxSmoothScalar n) :
    IntegrableOn
      (fun x => ∑ i : Fin (n + 1),
        smoothBoxProductFDeriv q v x (Pi.single i (1 : ℝ)) i)
      (Icc a b) := by
  have hfield : ∀ i : Fin (n + 1),
      IntegrableOn (fun x => q i x * (∂_{boxBasisVector i} v) x) (Icc a b) := by
    intro i
    exact ((q i).continuous.mul (∂_{boxBasisVector i} v).continuous).continuousOn
      |>.integrableOn_compact isCompact_Icc
  have hdiv :
      IntegrableOn (fun x => smoothBoxDivergence q x * v x) (Icc a b) := by
    exact ((smoothBoxDivergence q).continuous.mul v.continuous).continuousOn
      |>.integrableOn_compact isCompact_Icc
  have hsum :
      IntegrableOn
        (fun x => ∑ i : Fin (n + 1), q i x * (∂_{boxBasisVector i} v) x)
        (Icc a b) := by
    exact integrable_finsetSum _ (fun i _ => hfield i)
  exact (hsum.add hdiv).congr_fun
    (fun x hx => by
      simpa [smoothGreenVolumeTerm, smoothBoxVectorFunction, smoothBoxGradientFunction] using
        (smoothBoxProduct_divergence_eq_greenVolume q v x).symm)
    measurableSet_Icc

/-- Fully automatic smooth Green identity on the actual Schwartz core used by CACE's bounded-box
graph spaces. No caller-supplied derivative family, exceptional set, continuity proof,
integrability proof, or product-rule certificate remains. -/
theorem smoothBoxGreen_schwartz {n : Nat}
    {a b : BoxPoint n} (hle : a ≤ b)
    (q : BoxSmoothVector n) (v : BoxSmoothScalar n) :
    (∫ x in Icc a b,
      smoothGreenVolumeTerm (smoothBoxVectorFunction q) v
        (smoothBoxGradientFunction v) (smoothBoxDivergence q) x) =
      smoothNormalFluxPairing a b (smoothBoxVectorFunction q) v := by
  apply smoothBoxGreen hle
    (smoothBoxVectorFunction q) v (smoothBoxGradientFunction v) (smoothBoxDivergence q)
    (smoothBoxProductFDeriv q v) (∅ : Set (BoxPoint n)) Set.countable_empty
  · exact (smoothBoxProduct_continuous q v).continuousOn
  · intro x hx
    exact smoothBoxProduct_hasFDerivAt q v x
  · exact smoothBoxProduct_divergence_integrableOn a b q v
  · intro x
    exact smoothBoxProduct_divergence_eq_greenVolume q v x

/-- v3.30 endpoint: on the CACE smooth box core, the closure-level functional normal trace agrees
with the classical signed face-flux trace without any external local-calculus hypotheses. -/
theorem boxGraphNormalTrace_smooth_eq_classical_auto {n : Nat}
    {a b : BoxPoint n} (hle : a ≤ b)
    (q : BoxSmoothVector n) (v : BoxSmoothScalar n) :
    boxGraphNormalTrace a b (smoothBoxHDivClosedPoint a b q)
        (smoothBoxH1ClosedPoint a b v) =
      smoothBoxNormalTrace a b
        (scalarTimesVector v (smoothBoxVectorFunction q)) := by
  exact boxGraphNormalTrace_smooth_eq_classical hle q v
    (smoothBoxProductFDeriv q v) (∅ : Set (BoxPoint n)) Set.countable_empty
    (smoothBoxProduct_continuous q v).continuousOn
    (by
      intro x hx
      exact smoothBoxProduct_hasFDerivAt q v x)
    (smoothBoxProduct_divergence_integrableOn a b q v)
    (smoothBoxProduct_divergence_eq_greenVolume q v)

end

end Continuum

end CACEFormal
