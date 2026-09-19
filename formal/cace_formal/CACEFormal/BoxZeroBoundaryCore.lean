import CACEFormal.SmoothBoxGreenAuto

namespace CACEFormal

open Set Finset MeasureTheory
open scoped BigOperators

namespace Continuum

noncomputable section

/-!
# Concrete smooth zero-boundary scalar core on a rectangular box

The v3.40 closure theorem proves that graph-norm limits of any already-certified
zero-boundary core remain in the functional zero-boundary submodule.  This
module begins the missing concrete construction.

A Schwartz scalar belongs to `BoxBoundaryVanishingSmoothScalar a b` exactly
when its value vanishes pointwise on every upper and lower face of the closed
box.  This is a genuine restriction on the smooth scalar; arbitrary Schwartz
functions are not claimed to satisfy it.

The theorems below prove the classical consequence required by the later
functional extension: multiplying any smooth vector field by such a scalar has
zero signed normal flux on the box boundary.
-/

/-- A smooth scalar vanishes on every upper and lower face of the closed box. -/
def BoxBoundaryVanishes {n : Nat}
    (a b : BoxPoint n) (v : BoxSmoothScalar n) : Prop :=
  ∀ i : Fin (n + 1),
    (∀ x ∈ Icc (a ∘ i.succAbove) (b ∘ i.succAbove),
      v (i.insertNth (b i) x) = 0) ∧
    (∀ x ∈ Icc (a ∘ i.succAbove) (b ∘ i.succAbove),
      v (i.insertNth (a i) x) = 0)

/-- Smooth Schwartz scalars with zero value on every box face form a real
linear submodule. -/
noncomputable def BoxBoundaryVanishingSmoothScalar {n : Nat}
    (a b : BoxPoint n) : Submodule ℝ (BoxSmoothScalar n) where
  carrier := {v | BoxBoundaryVanishes a b v}
  zero_mem' := by
    intro i
    constructor <;> intro x hx <;> simp
  add_mem' := by
    intro v w hv hw
    intro i
    constructor
    · intro x hx
      have hvx := (hv i).1 x hx
      have hwx := (hw i).1 x hx
      simp [hvx, hwx]
    · intro x hx
      have hvx := (hv i).2 x hx
      have hwx := (hw i).2 x hx
      simp [hvx, hwx]
  smul_mem' := by
    intro c v hv
    intro i
    constructor
    · intro x hx
      have hvx := (hv i).1 x hx
      simp [hvx]
    · intro x hx
      have hvx := (hv i).2 x hx
      simp [hvx]

/-- Membership in the concrete smooth zero-boundary core is exactly pointwise
vanishing on every upper and lower face. -/
@[simp]
theorem mem_BoxBoundaryVanishingSmoothScalar_iff {n : Nat}
    (a b : BoxPoint n) (v : BoxSmoothScalar n) :
    v ∈ BoxBoundaryVanishingSmoothScalar a b ↔
      BoxBoundaryVanishes a b v :=
  Iff.rfl

/-- On every upper face, multiplying by a boundary-vanishing scalar kills the
normal-coordinate integrand pointwise. -/
theorem scalarTimesVector_upperFace_eq_zero_of_boundaryVanishes {n : Nat}
    (a b : BoxPoint n)
    (v : BoxSmoothScalar n)
    (hv : v ∈ BoxBoundaryVanishingSmoothScalar a b)
    (q : BoxSmoothVector n)
    (i : Fin (n + 1))
    (x : BoxFacePoint n)
    (hx : x ∈ Icc (a ∘ i.succAbove) (b ∘ i.succAbove)) :
    scalarTimesVector v (smoothBoxVectorFunction q)
        (i.insertNth (b i) x) i = 0 := by
  change BoxBoundaryVanishes a b v at hv
  have hvx := (hv i).1 x hx
  simp [scalarTimesVector, smoothBoxVectorFunction, hvx]

/-- Lower-face analogue of
`scalarTimesVector_upperFace_eq_zero_of_boundaryVanishes`. -/
theorem scalarTimesVector_lowerFace_eq_zero_of_boundaryVanishes {n : Nat}
    (a b : BoxPoint n)
    (v : BoxSmoothScalar n)
    (hv : v ∈ BoxBoundaryVanishingSmoothScalar a b)
    (q : BoxSmoothVector n)
    (i : Fin (n + 1))
    (x : BoxFacePoint n)
    (hx : x ∈ Icc (a ∘ i.succAbove) (b ∘ i.succAbove)) :
    scalarTimesVector v (smoothBoxVectorFunction q)
        (i.insertNth (a i) x) i = 0 := by
  change BoxBoundaryVanishes a b v at hv
  have hvx := (hv i).2 x hx
  simp [scalarTimesVector, smoothBoxVectorFunction, hvx]

/-- Every upper-face flux of the product field is zero. -/
theorem upperFaceFlux_scalarTimesVector_eq_zero_of_boundaryVanishes {n : Nat}
    (a b : BoxPoint n)
    (v : BoxSmoothScalar n)
    (hv : v ∈ BoxBoundaryVanishingSmoothScalar a b)
    (q : BoxSmoothVector n)
    (i : Fin (n + 1)) :
    upperFaceFlux a b
      (scalarTimesVector v (smoothBoxVectorFunction q)) i = 0 := by
  unfold upperFaceFlux
  calc
    (∫ x in Icc (a ∘ i.succAbove) (b ∘ i.succAbove),
      scalarTimesVector v (smoothBoxVectorFunction q)
        (i.insertNth (b i) x) i) =
        ∫ x in Icc (a ∘ i.succAbove) (b ∘ i.succAbove), (0 : ℝ) := by
          apply setIntegral_congr_fun measurableSet_Icc
          intro x hx
          exact scalarTimesVector_upperFace_eq_zero_of_boundaryVanishes
            a b v hv q i x hx
    _ = 0 := by simp

/-- Every lower-face flux of the product field is zero. -/
theorem lowerFaceFlux_scalarTimesVector_eq_zero_of_boundaryVanishes {n : Nat}
    (a b : BoxPoint n)
    (v : BoxSmoothScalar n)
    (hv : v ∈ BoxBoundaryVanishingSmoothScalar a b)
    (q : BoxSmoothVector n)
    (i : Fin (n + 1)) :
    lowerFaceFlux a b
      (scalarTimesVector v (smoothBoxVectorFunction q)) i = 0 := by
  unfold lowerFaceFlux
  calc
    (∫ x in Icc (a ∘ i.succAbove) (b ∘ i.succAbove),
      scalarTimesVector v (smoothBoxVectorFunction q)
        (i.insertNth (a i) x) i) =
        ∫ x in Icc (a ∘ i.succAbove) (b ∘ i.succAbove), (0 : ℝ) := by
          apply setIntegral_congr_fun measurableSet_Icc
          intro x hx
          exact scalarTimesVector_lowerFace_eq_zero_of_boundaryVanishes
            a b v hv q i x hx
    _ = 0 := by simp

/-- A boundary-vanishing smooth scalar kills the classical normal trace of its
product with every smooth box vector field. -/
theorem smoothBoxNormalTrace_scalarTimesVector_eq_zero_of_boundaryVanishes
    {n : Nat}
    (a b : BoxPoint n)
    (v : BoxSmoothScalar n)
    (hv : v ∈ BoxBoundaryVanishingSmoothScalar a b)
    (q : BoxSmoothVector n) :
    smoothBoxNormalTrace a b
      (scalarTimesVector v (smoothBoxVectorFunction q)) = 0 := by
  unfold smoothBoxNormalTrace
  apply Finset.sum_eq_zero
  intro i hi
  rw [
    upperFaceFlux_scalarTimesVector_eq_zero_of_boundaryVanishes a b v hv q i,
    lowerFaceFlux_scalarTimesVector_eq_zero_of_boundaryVanishes a b v hv q i,
  ]
  simp

/-- Equivalent boundary-pairing form of the zero classical normal-flux result. -/
theorem smoothNormalFluxPairing_eq_zero_of_boundaryVanishes {n : Nat}
    (a b : BoxPoint n)
    (v : BoxSmoothScalar n)
    (hv : v ∈ BoxBoundaryVanishingSmoothScalar a b)
    (q : BoxSmoothVector n) :
    smoothNormalFluxPairing a b (smoothBoxVectorFunction q) v = 0 := by
  rw [smoothNormalFluxPairing_eq_trace_product]
  exact smoothBoxNormalTrace_scalarTimesVector_eq_zero_of_boundaryVanishes
    a b v hv q

end

end Continuum

end CACEFormal
