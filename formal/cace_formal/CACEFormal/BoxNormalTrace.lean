import CACEFormal.SmoothBoxGreen

namespace CACEFormal

open Set Finset MeasureTheory
open scoped BigOperators

namespace Continuum

/-- Outward flux through the upper face normal to coordinate `i`. -/
noncomputable def upperFaceFlux {n : Nat}
    (a b : BoxPoint n) (f : BoxPoint n → BoxPoint n) (i : Fin (n + 1)) : ℝ :=
  ∫ x in Icc (a ∘ i.succAbove) (b ∘ i.succAbove),
    f (i.insertNth (b i) x) i

/-- Outward flux through the lower face normal to coordinate `i`, before the outward minus sign. -/
noncomputable def lowerFaceFlux {n : Nat}
    (a b : BoxPoint n) (f : BoxPoint n → BoxPoint n) (i : Fin (n + 1)) : ℝ :=
  ∫ x in Icc (a ∘ i.succAbove) (b ∘ i.succAbove),
    f (i.insertNth (a i) x) i

/-- Classical normal trace pairing on a rectangular box, represented by signed face fluxes. -/
noncomputable def smoothBoxNormalTrace {n : Nat}
    (a b : BoxPoint n) (f : BoxPoint n → BoxPoint n) : ℝ :=
  ∑ i : Fin (n + 1), upperFaceFlux a b f i - lowerFaceFlux a b f i

/-- The explicit normal-trace representation agrees definitionally with the flux term used by Green's theorem. -/
theorem smoothBoxNormalTrace_eq_signedBoxFlux {n : Nat}
    (a b : BoxPoint n) (f : BoxPoint n → BoxPoint n) :
    smoothBoxNormalTrace a b f = signedBoxFlux a b f := by
  rfl

/--
For a classically differentiable vector field, the smooth normal trace equals the
volume integral of its divergence.  This is a theorem, not a stored trace axiom.
-/
theorem smoothBoxNormalTrace_eq_integral_divergence {n : Nat}
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
    smoothBoxNormalTrace a b f =
      ∫ x in Icc a b,
        ∑ i : Fin (n + 1), f' x (Pi.single i (1 : ℝ)) i := by
  rw [smoothBoxNormalTrace_eq_signedBoxFlux]
  exact (smoothBoxDivergenceGreen hle f f' s hs Hc Hd Hi).symm

/-- The zero field has zero smooth normal trace on every box. -/
@[simp]
theorem smoothBoxNormalTrace_zero {n : Nat} (a b : BoxPoint n) :
    smoothBoxNormalTrace a b (fun _ => (0 : BoxPoint n)) = 0 := by
  simp [smoothBoxNormalTrace, upperFaceFlux, lowerFaceFlux]

/-- The scalar/vector boundary pairing is exactly the normal trace of the product field. -/
theorem smoothNormalFluxPairing_eq_trace_product {n : Nat}
    (a b : BoxPoint n) (q : BoxPoint n → BoxPoint n)
    (v : BoxPoint n → ℝ) :
    smoothNormalFluxPairing a b q v =
      smoothBoxNormalTrace a b (scalarTimesVector v q) := by
  rfl

end Continuum

end CACEFormal
