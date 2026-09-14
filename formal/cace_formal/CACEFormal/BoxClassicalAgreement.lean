import CACEFormal.BoxGraphGreenPairing
import Mathlib.MeasureTheory.Function.L2Space

namespace CACEFormal

open Set Finset MeasureTheory Filter
open scoped BigOperators InnerProductSpace LineDeriv SchwartzMap

namespace Continuum

noncomputable section

/-!
# Classical interpretation of the bounded-box graph pairing

The box graph spaces are built from `L²` for `volume.restrict (Icc a b)`.  The lemmas here expose
that Hilbert pairing as the ordinary box integral used by the classical Green theorem.  This is the
non-definitional bridge needed before identifying the closure-level functional trace with signed
face flux.
-/

/-- The restricted-box L² inner product of two Schwartz fields is their classical product integral. -/
theorem boxSchwartzL2_inner_eq_setIntegral_mul {n : Nat}
    (a b : BoxPoint n) (f g : BoxSmoothScalar n) :
    inner ℝ (boxSchwartzL2 a b f) (boxSchwartzL2 a b g) =
      ∫ x in Icc a b, f x * g x := by
  rw [MeasureTheory.L2.inner_def]
  apply integral_congr_ae
  have hf :
      (boxSchwartzL2 a b f : BoxPoint n → ℝ) =ᵐ[boxVolume a b] f := by
    simpa [boxSchwartzL2] using f.coeFn_toLp 2 (boxVolume a b)
  have hg :
      (boxSchwartzL2 a b g : BoxPoint n → ℝ) =ᵐ[boxVolume a b] g := by
    simpa [boxSchwartzL2] using g.coeFn_toLp 2 (boxVolume a b)
  filter_upwards [hf, hg] with x hfx hgx
  simp [hfx, hgx, RCLike.inner_apply, mul_comm]

/-- Smooth divergence as a Schwartz scalar field. -/
noncomputable def smoothBoxDivergence {n : Nat} (q : BoxSmoothVector n) :
    BoxSmoothScalar n :=
  ∑ i : Fin (n + 1), ∂_{boxBasisVector i} (q i)

/-- The divergence coordinate in the smooth box graph is exactly the L² image of smooth divergence. -/
theorem smoothBoxHDivGraphMap_divergence {n : Nat}
    (a b : BoxPoint n) (q : BoxSmoothVector n) :
    (smoothBoxHDivGraphMap a b q).2 =
      boxSchwartzL2 a b (smoothBoxDivergence q) := by
  simp [smoothBoxHDivGraphMap, smoothBoxDivergence]

/-- The field coordinate in the smooth H(div) box graph is the corresponding restricted L² field. -/
theorem smoothBoxHDivGraphMap_field {n : Nat}
    (a b : BoxPoint n) (q : BoxSmoothVector n) (i : Fin (n + 1)) :
    (smoothBoxHDivGraphMap a b q).1 i = boxSchwartzL2 a b (q i) := by
  rfl

/-- The value coordinate in the smooth H¹ box graph is the restricted L² scalar field. -/
theorem smoothBoxH1GraphMap_value {n : Nat}
    (a b : BoxPoint n) (v : BoxSmoothScalar n) :
    (smoothBoxH1GraphMap a b v).1 = boxSchwartzL2 a b v := by
  rfl

/-- The gradient coordinate in the smooth H¹ box graph is the restricted L² weak/classical derivative. -/
theorem smoothBoxH1GraphMap_gradient {n : Nat}
    (a b : BoxPoint n) (v : BoxSmoothScalar n) (i : Fin (n + 1)) :
    (smoothBoxH1GraphMap a b v).2 i =
      boxSchwartzL2 a b (∂_{boxBasisVector i} v) := by
  rfl

/-- The divergence/value part of the graph Green pairing has its classical box-integral form. -/
theorem boxSmooth_div_value_pairing_eq_integral {n : Nat}
    (a b : BoxPoint n) (q : BoxSmoothVector n) (v : BoxSmoothScalar n) :
    inner ℝ (smoothBoxHDivGraphMap a b q).2 (smoothBoxH1GraphMap a b v).1 =
      ∫ x in Icc a b, smoothBoxDivergence q x * v x := by
  rw [smoothBoxHDivGraphMap_divergence, smoothBoxH1GraphMap_value]
  exact boxSchwartzL2_inner_eq_setIntegral_mul a b (smoothBoxDivergence q) v

/-- Each field/gradient coordinate pairing has its classical box-integral form. -/
theorem boxSmooth_field_gradient_pairing_eq_integral {n : Nat}
    (a b : BoxPoint n) (q : BoxSmoothVector n) (v : BoxSmoothScalar n)
    (i : Fin (n + 1)) :
    inner ℝ (smoothBoxHDivGraphMap a b q).1 i (smoothBoxH1GraphMap a b v).2 i =
      ∫ x in Icc a b, q i x * (∂_{boxBasisVector i} v) x := by
  rw [smoothBoxHDivGraphMap_field, smoothBoxH1GraphMap_gradient]
  exact boxSchwartzL2_inner_eq_setIntegral_mul a b (q i) (∂_{boxBasisVector i} v)

end

end Continuum

end CACEFormal
