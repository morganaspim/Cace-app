import CACEFormal.ContinuumGraphSpaces
import Mathlib.MeasureTheory.Integral.DivergenceTheorem

namespace CACEFormal

open Set Finset MeasureTheory
open scoped BigOperators

namespace Continuum

/-- Coordinate model for an `(n+1)`-dimensional rectangular box. -/
abbrev BoxPoint (n : Nat) := Fin (n + 1) → ℝ

/-- Coordinate model for one codimension-one face of an `(n+1)`-box. -/
abbrev BoxFacePoint (n : Nat) := Fin n → ℝ

/-- Signed outward flux through all faces of a rectangular box. -/
noncomputable def signedBoxFlux {n : Nat}
    (a b : BoxPoint n) (f : BoxPoint n → BoxPoint n) : ℝ :=
  ∑ i : Fin (n + 1),
    ((∫ x in Icc (a ∘ i.succAbove) (b ∘ i.succAbove),
        f (i.insertNth (b i) x) i) -
      ∫ x in Icc (a ∘ i.succAbove) (b ∘ i.succAbove),
        f (i.insertNth (a i) x) i)

/--
A direct CACE wrapper around Mathlib's Bochner divergence theorem on a rectangular box.
This is the smooth/classical Green-flux identity that will seed the normal-trace extension.
-/
theorem smoothBoxDivergenceGreen {n : Nat}
    {a b : BoxPoint n} (hle : a ≤ b)
    (f : BoxPoint n → BoxPoint n)
    (f' : BoxPoint n → BoxPoint n →L[ℝ] BoxPoint n)
    (s : Set (BoxPoint n)) (hs : s.Countable)
    (Hc : ContinuousOn f (Icc a b))
    (Hd : ∀ x ∈ (Set.pi univ fun i => Ioo (a i) (b i)) \ s,
      HasFDerivAt f (f' x) x)
    (Hi : IntegrableOn
      (fun x => ∑ i : Fin (n + 1), f' x (Pi.single i (1 : ℝ)) i)
      (Icc a b)) :
    (∫ x in Icc a b,
      ∑ i : Fin (n + 1), f' x (Pi.single i (1 : ℝ)) i) =
      signedBoxFlux a b f := by
  simpa [signedBoxFlux] using
    (MeasureTheory.integral_divergence_of_hasFDerivAt_off_countable
      (E := ℝ) hle f f' s hs Hc Hd Hi)

/-- Product vector field used in the scalar/vector Green formula. -/
def scalarTimesVector {n : Nat}
    (v : BoxPoint n → ℝ) (q : BoxPoint n → BoxPoint n) :
    BoxPoint n → BoxPoint n :=
  fun x i => v x * q x i

/-- Boundary pairing `∫_{∂Ω} v (q·n)` represented as the signed face sum on a box. -/
noncomputable def smoothNormalFluxPairing {n : Nat}
    (a b : BoxPoint n) (q : BoxPoint n → BoxPoint n)
    (v : BoxPoint n → ℝ) : ℝ :=
  signedBoxFlux a b (scalarTimesVector v q)

/--
Green's formula once the classical product derivative has been identified pointwise.
The boundary term itself is *derived* from Mathlib's divergence theorem; the remaining
`hprod` obligation is exactly the local product-rule/divergence calculation and is kept
explicit so later releases can discharge it from smoother field structures.
-/
theorem smoothBoxGreen_of_product_divergence {n : Nat}
    {a b : BoxPoint n} (hle : a ≤ b)
    (q : BoxPoint n → BoxPoint n) (v : BoxPoint n → ℝ)
    (F' : BoxPoint n → BoxPoint n →L[ℝ] BoxPoint n)
    (volumeTerm : BoxPoint n → ℝ)
    (s : Set (BoxPoint n)) (hs : s.Countable)
    (Hc : ContinuousOn (scalarTimesVector v q) (Icc a b))
    (Hd : ∀ x ∈ (Set.pi univ fun i => Ioo (a i) (b i)) \ s,
      HasFDerivAt (scalarTimesVector v q) (F' x) x)
    (Hi : IntegrableOn
      (fun x => ∑ i : Fin (n + 1), F' x (Pi.single i (1 : ℝ)) i)
      (Icc a b))
    (hprod : ∀ x,
      (∑ i : Fin (n + 1), F' x (Pi.single i (1 : ℝ)) i) = volumeTerm x) :
    (∫ x in Icc a b, volumeTerm x) = smoothNormalFluxPairing a b q v := by
  have hdiv := smoothBoxDivergenceGreen hle (scalarTimesVector v q) F' s hs Hc Hd Hi
  rw [← hdiv]
  apply setIntegral_congr_fun measurableSet_Icc
  intro x hx
  exact hprod x

end Continuum

end CACEFormal
