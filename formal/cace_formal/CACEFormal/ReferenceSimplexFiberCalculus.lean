import Mathlib
import CACEFormal.ReferenceSimplexFiber
import CACEFormal.SimplexEuclideanL2

namespace CACEFormal

open Set MeasureTheory
open scoped BigOperators LineDeriv Interval

namespace Continuum

noncomputable section

/-!
# One-dimensional calculus on reference-simplex coordinate fibers

This module is the analytic bridge from the exact coordinate-fiber geometry in
`ReferenceSimplexFiber` to one-dimensional integration by parts.

The key objects are deliberately concrete:

* the coordinate fiber itself has derivative `eᵢ`;
* an affine P1 scalar restricts to `A + gradᵢ * t`;
* an RT0 coordinate restricts to `cᵢ + radial * t`;
* therefore their one-dimensional derivatives are exactly the expected finite
  element coefficients.

No Sobolev or Gauss--Green theorem is assumed here.  These are elementary
finite-dimensional identities that will feed the later interval integral proof.
-/

/-- The lower endpoint of an admissible coordinate fiber belongs to the reference simplex. -/
theorem referenceSimplexFiberPoint_zero_mem
    {d : Nat} (i : Fin d) (x : EuclideanDomain d)
    (hother :
      ∀ j ∈ Finset.univ.erase i, 0 ≤ EuclideanSpace.proj j x)
    (hupper : 0 ≤ referenceSimplexFiberUpper i x) :
    referenceSimplexFiberPoint i x 0 ∈ euclideanReferenceSimplex d := by
  rw [referenceSimplexFiberPoint_mem_iff i x 0 hother]
  exact ⟨le_rfl, hupper⟩

/-- The upper endpoint of an admissible coordinate fiber belongs to the reference simplex. -/
theorem referenceSimplexFiberPoint_upper_mem
    {d : Nat} (i : Fin d) (x : EuclideanDomain d)
    (hother :
      ∀ j ∈ Finset.univ.erase i, 0 ≤ EuclideanSpace.proj j x)
    (hupper : 0 ≤ referenceSimplexFiberUpper i x) :
    referenceSimplexFiberPoint i x (referenceSimplexFiberUpper i x) ∈
      euclideanReferenceSimplex d := by
  rw [referenceSimplexFiberPoint_mem_iff
    i x (referenceSimplexFiberUpper i x) hother]
  exact ⟨hupper, le_rfl⟩

/-- The coordinate fiber is an affine line with constant derivative `eᵢ`. -/
theorem referenceSimplexFiberPoint_hasDerivAt
    {d : Nat} (i : Fin d) (x : EuclideanDomain d) (t : ℝ) :
    HasDerivAt (referenceSimplexFiberPoint i x) (basisVector i) t := by
  have hscalar :
      HasDerivAt
        (fun s : ℝ => s - EuclideanSpace.proj i x) 1 t :=
    (hasDerivAt_id' t).sub_const (EuclideanSpace.proj i x)
  simpa [referenceSimplexFiberPoint, one_smul] using
    (hscalar.smul_const (basisVector i)).const_add x

/-- Constant part of an affine P1 scalar after the selected coordinate is removed. -/
def referenceSimplexP1FiberBase
    {d : Nat} (u : AffineScalar d) (i : Fin d) (x : EuclideanDomain d) : ℝ :=
  u.c +
    ∑ j ∈ Finset.univ.erase i,
      u.grad j * EuclideanSpace.proj j x

/-- Restriction of a P1 affine scalar to one coordinate fiber. -/
def referenceSimplexP1Fiber
    {d : Nat} (u : AffineScalar d) (i : Fin d) (x : EuclideanDomain d) :
    ℝ → ℝ :=
  fun t => euclideanAffineScalarEval u (referenceSimplexFiberPoint i x t)

/--
Exact affine formula for a P1 field along a coordinate fiber:
`u(x[i := t]) = A + gradᵢ * t`.
-/
theorem referenceSimplexP1Fiber_eq_affine
    {d : Nat} (u : AffineScalar d) (i : Fin d)
    (x : EuclideanDomain d) (t : ℝ) :
    referenceSimplexP1Fiber u i x t =
      referenceSimplexP1FiberBase u i x + u.grad i * t := by
  have hsum :
      (∑ j ∈ Finset.univ.erase i,
          u.grad j *
            EuclideanSpace.proj j (referenceSimplexFiberPoint i x t)) =
        ∑ j ∈ Finset.univ.erase i,
          u.grad j * EuclideanSpace.proj j x := by
    apply Finset.sum_congr rfl
    intro j hj
    rw [referenceSimplexFiberPoint_proj_ne i j x t
      (Finset.mem_erase.mp hj).1]
  unfold referenceSimplexP1Fiber euclideanAffineScalarEval
  rw [← Finset.sum_erase_add Finset.univ
    (fun j : Fin d =>
      u.grad j *
        EuclideanSpace.proj j (referenceSimplexFiberPoint i x t))
    (Finset.mem_univ i)]
  rw [hsum, referenceSimplexFiberPoint_proj_same]
  unfold referenceSimplexP1FiberBase
  ring

/-- The exact one-dimensional derivative of a P1 field along coordinate `i`. -/
theorem referenceSimplexP1Fiber_hasDerivAt
    {d : Nat} (u : AffineScalar d) (i : Fin d)
    (x : EuclideanDomain d) (t : ℝ) :
    HasDerivAt (referenceSimplexP1Fiber u i x) (u.grad i) t := by
  have hfun :
      referenceSimplexP1Fiber u i x =
        fun s : ℝ =>
          referenceSimplexP1FiberBase u i x + u.grad i * s := by
    funext s
    exact referenceSimplexP1Fiber_eq_affine u i x s
  rw [hfun]
  exact
    (hasDerivAt_const_mul (x := t) (u.grad i)).const_add
      (referenceSimplexP1FiberBase u i x)

/-- Restriction of one RT0 coordinate to one coordinate fiber. -/
def referenceSimplexRT0Fiber
    {d : Nat} (q : RT0AffineND d) (i : Fin d) (x : EuclideanDomain d) :
    ℝ → ℝ :=
  fun t => euclideanRT0ComponentEval q i (referenceSimplexFiberPoint i x t)

/-- Exact affine formula for one RT0 coordinate along its matching coordinate fiber. -/
theorem referenceSimplexRT0Fiber_eq_affine
    {d : Nat} (q : RT0AffineND d) (i : Fin d)
    (x : EuclideanDomain d) (t : ℝ) :
    referenceSimplexRT0Fiber q i x t =
      q.c i + q.radial * t := by
  simp [referenceSimplexRT0Fiber, euclideanRT0ComponentEval]

/-- The exact one-dimensional derivative of the matching RT0 coordinate is its radial coefficient. -/
theorem referenceSimplexRT0Fiber_hasDerivAt
    {d : Nat} (q : RT0AffineND d) (i : Fin d)
    (x : EuclideanDomain d) (t : ℝ) :
    HasDerivAt (referenceSimplexRT0Fiber q i x) q.radial t := by
  have hfun :
      referenceSimplexRT0Fiber q i x =
        fun s : ℝ => q.c i + q.radial * s := by
    funext s
    exact referenceSimplexRT0Fiber_eq_affine q i x s
  rw [hfun]
  exact
    (hasDerivAt_const_mul (x := t) q.radial).const_add (q.c i)

end

end Continuum

end CACEFormal
