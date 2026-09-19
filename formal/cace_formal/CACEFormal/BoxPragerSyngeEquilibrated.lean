import CACEFormal.BoxPragerSynge
import Mathlib.Analysis.InnerProductSpace.PiL2

namespace CACEFormal

open scoped BigOperators InnerProductSpace

namespace Continuum

noncomputable section

/-!
# Equilibrated bounded-box Prager--Synge bridge

The existing bounded-box Prager--Synge endpoint accepts an abstract cross-term
identity.  This module discharges that identity directly from the closed graph
coordinates in the important equilibrated case where the H(div) error datum has
zero divergence coordinate.

The vector error space is deliberately `PiLp 2`, not the raw function space,
so the norm and inner product are the canonical finite L² product norm.
-/

/-- Canonical finite L² product for vector-valued box errors. -/
abbrev BoxVectorL2 {n : Nat} (a b : BoxPoint n) :=
  PiLp 2 (fun _ : Fin (n + 1) => BoxL2 a b)

/-- Flux-field coordinate of a closed H(div) graph datum in the canonical vector L² space. -/
noncomputable def boxHDivFieldError {n : Nat} (a b : BoxPoint n)
    (q : BoxHDivGraphClosedSpace a b) : BoxVectorL2 a b :=
  WithLp.toLp 2 q.1.1

/-- Gradient coordinate of a closed H¹ graph datum in the canonical vector L² space. -/
noncomputable def boxH1GradientError {n : Nat} (a b : BoxPoint n)
    (v : BoxH1GraphClosedSpace a b) : BoxVectorL2 a b :=
  WithLp.toLp 2 v.1.2

/-- Coordinate formula for the closed bounded-box Green pairing. -/
theorem closedBoxGraphGreenPairing_apply_closed {n : Nat}
    (a b : BoxPoint n)
    (q : BoxHDivGraphClosedSpace a b)
    (v : BoxH1GraphClosedSpace a b) :
    closedBoxGraphGreenPairing a b q v =
      (∑ i : Fin (n + 1), inner ℝ (q.1.1 i) (v.1.2 i)) +
        inner ℝ q.1.2 v.1.1 := by
  change ambientBoxGraphGreenPairing a b q.1 v.1 = _
  exact ambientBoxGraphGreenPairing_apply a b q.1 v.1

/--
For an equilibrated H(div) error datum, the bounded-box Green pairing is exactly
the Hilbert inner product between the gradient and flux-field error vectors.
-/
theorem boxGradientFlux_inner_eq_green_of_divergence_zero {n : Nat}
    (a b : BoxPoint n)
    (q : BoxHDivGraphClosedSpace a b)
    (v : BoxH1GraphClosedSpace a b)
    (hdiv : q.1.2 = 0) :
    inner ℝ (boxH1GradientError a b v) (boxHDivFieldError a b q) =
      closedBoxGraphGreenPairing a b q v := by
  rw [closedBoxGraphGreenPairing_apply_closed, hdiv]
  simp only [inner_zero_left, add_zero]
  rw [PiLp.inner_apply]
  apply Finset.sum_congr rfl
  intro i hi
  simp only [boxH1GradientError, boxHDivFieldError, PiLp.toLp_apply]
  exact real_inner_comm _ _

/--
Concrete bounded-box Prager--Synge identity for an equilibrated flux error.
The cross-term hypothesis is derived internally from the graph coordinates.
-/
theorem boxGraphPragerSynge_of_divergence_zero {n : Nat}
    (a b : BoxPoint n)
    (q : BoxHDivGraphClosedSpace a b)
    (v : BoxH1GraphClosedSpace a b)
    (hv : HasZeroBoundaryTrace (boxGraphBoundedGreenPairing a b) v)
    (hdiv : q.1.2 = 0) :
    ‖boxH1GradientError a b v + boxHDivFieldError a b q‖ *
        ‖boxH1GradientError a b v + boxHDivFieldError a b q‖ =
      ‖boxH1GradientError a b v‖ * ‖boxH1GradientError a b v‖ +
        ‖boxHDivFieldError a b q‖ * ‖boxHDivFieldError a b q‖ := by
  apply boxGraphPragerSynge a b q v hv
  simpa [boxGraphBoundedGreenPairing] using
    boxGradientFlux_inner_eq_green_of_divergence_zero a b q v hdiv

end

end Continuum

end CACEFormal
