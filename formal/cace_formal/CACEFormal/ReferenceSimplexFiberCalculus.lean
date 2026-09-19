import Mathlib
import CACEFormal.ReferenceSimplexFiber
import CACEFormal.SimplexEuclideanL2

namespace CACEFormal

open Set MeasureTheory
open scoped BigOperators Interval LineDeriv

namespace Continuum

noncomputable section

/-!
# One-dimensional calculus on reference-simplex coordinate fibers

This module is the analytic companion to `ReferenceSimplexFiber`.  It keeps the
geometry layer small and proves the facts needed for the reference-simplex
Gauss--Green argument:

* the coordinate-fiber map is an affine line with derivative `e_i`;
* the lower and upper endpoints remain in the reference simplex;
* P1 and RT0 restrictions to a coordinate fiber are one-dimensional affine maps;
* Schwartz test functions restrict differentiably to the same line, with derivative
  equal to the ambient coordinate directional derivative;
* the resulting P1 and RT0 products satisfy exact interval integration by parts.

These statements are still local to one coordinate fiber.  Fubini and the
identification of the endpoint terms with oriented facet currents are the next layer.
-/

/-- Replacing coordinate `i` by its original value returns the original point. -/
@[simp]
theorem referenceSimplexFiberPoint_original {d : Nat}
    (i : Fin d) (x : EuclideanDomain d) :
    referenceSimplexFiberPoint i x (EuclideanSpace.proj i x) = x := by
  simp [referenceSimplexFiberPoint]

/-- The coordinate-fiber parameterization is continuous. -/
theorem referenceSimplexFiberPoint_continuous {d : Nat}
    (i : Fin d) (x : EuclideanDomain d) :
    Continuous (referenceSimplexFiberPoint i x) := by
  unfold referenceSimplexFiberPoint
  fun_prop

/-- The fiber line has constant velocity equal to the canonical basis vector `e_i`. -/
theorem referenceSimplexFiberPoint_hasDerivAt {d : Nat}
    (i : Fin d) (x : EuclideanDomain d) (t : ℝ) :
    HasDerivAt (referenceSimplexFiberPoint i x) (basisVector i) t := by
  have hsub :
      HasDerivAt
        (fun s : ℝ => s - EuclideanSpace.proj i x)
        1 t :=
    (hasDerivAt_id' (x := t)).sub_const _
  have hline := hsub.smul_const (basisVector i)
  have hconst : HasDerivAt (fun _ : ℝ => x) 0 t :=
    hasDerivAt_const t x
  simpa [referenceSimplexFiberPoint] using hconst.add hline

/-- The lower endpoint of every nonempty coordinate fiber belongs to the simplex. -/
theorem referenceSimplexFiberPoint_zero_mem_of_mem
    {d : Nat} (i : Fin d) {x : EuclideanDomain d}
    (hx : x ∈ euclideanReferenceSimplex d) :
    referenceSimplexFiberPoint i x 0 ∈ euclideanReferenceSimplex d := by
  have hf := (mem_euclideanReferenceSimplex_iff_fiber i x).mp hx
  apply (referenceSimplexFiberPoint_mem_iff i x 0 hf.1).2
  exact ⟨le_rfl, referenceSimplexFiberUpper_nonneg_of_mem i hx⟩

/-- The upper endpoint of every nonempty coordinate fiber belongs to the simplex. -/
theorem referenceSimplexFiberPoint_upper_mem_of_mem
    {d : Nat} (i : Fin d) {x : EuclideanDomain d}
    (hx : x ∈ euclideanReferenceSimplex d) :
    referenceSimplexFiberPoint i x (referenceSimplexFiberUpper i x) ∈
      euclideanReferenceSimplex d := by
  have hf := (mem_euclideanReferenceSimplex_iff_fiber i x).mp hx
  apply
    (referenceSimplexFiberPoint_mem_iff
      i x (referenceSimplexFiberUpper i x) hf.1).2
  exact ⟨referenceSimplexFiberUpper_nonneg_of_mem i hx, le_rfl⟩

/--
An affine P1 function restricted to a coordinate fiber is an affine function of
the scalar fiber parameter.
-/
theorem euclideanAffineScalarEval_fiberPoint_formula
    {d : Nat} (u : AffineScalar d)
    (i : Fin d) (x : EuclideanDomain d) (t : ℝ) :
    euclideanAffineScalarEval u (referenceSimplexFiberPoint i x t) =
      u.c +
        ((∑ j ∈ Finset.univ.erase i,
            u.grad j * EuclideanSpace.proj j x) +
          u.grad i * t) := by
  unfold euclideanAffineScalarEval
  rw [← Finset.sum_erase_add Finset.univ
    (fun j : Fin d =>
      u.grad j *
        EuclideanSpace.proj j (referenceSimplexFiberPoint i x t))
    (Finset.mem_univ i)]
  have hother :
      (∑ j ∈ Finset.univ.erase i,
        u.grad j *
          EuclideanSpace.proj j (referenceSimplexFiberPoint i x t)) =
      ∑ j ∈ Finset.univ.erase i,
        u.grad j * EuclideanSpace.proj j x := by
    apply Finset.sum_congr rfl
    intro j hj
    rw [referenceSimplexFiberPoint_proj_ne i j x t
      (Finset.mem_erase.mp hj).1]
  rw [hother, referenceSimplexFiberPoint_proj_same]

/-- Exact finite-difference formula for a P1 restriction along one fiber. -/
theorem euclideanAffineScalarEval_fiberPoint_sub
    {d : Nat} (u : AffineScalar d)
    (i : Fin d) (x : EuclideanDomain d) (s t : ℝ) :
    euclideanAffineScalarEval u (referenceSimplexFiberPoint i x t) -
        euclideanAffineScalarEval u (referenceSimplexFiberPoint i x s) =
      u.grad i * (t - s) := by
  rw [euclideanAffineScalarEval_fiberPoint_formula,
    euclideanAffineScalarEval_fiberPoint_formula]
  ring

/-- The exact one-dimensional derivative of a P1 restriction is its `i`-th gradient coordinate. -/
theorem euclideanAffineScalarEval_fiberPoint_hasDerivAt
    {d : Nat} (u : AffineScalar d)
    (i : Fin d) (x : EuclideanDomain d) (t : ℝ) :
    HasDerivAt
      (fun s => euclideanAffineScalarEval u (referenceSimplexFiberPoint i x s))
      (u.grad i) t := by
  let A : ℝ :=
    u.c +
      ∑ j ∈ Finset.univ.erase i,
        u.grad j * EuclideanSpace.proj j x
  have hconst : HasDerivAt (fun _ : ℝ => A) 0 t :=
    hasDerivAt_const t A
  have hlinear :
      HasDerivAt (fun s : ℝ => u.grad i * s) (u.grad i) t :=
    hasDerivAt_const_mul (x := t) (u.grad i)
  simpa [A, euclideanAffineScalarEval_fiberPoint_formula] using
    hconst.add hlinear

/-- The selected RT0 coordinate restricts to `q.c i + q.radial * t`. -/
@[simp]
theorem euclideanRT0ComponentEval_fiberPoint_same
    {d : Nat} (q : RT0AffineND d)
    (i : Fin d) (x : EuclideanDomain d) (t : ℝ) :
    euclideanRT0ComponentEval q i (referenceSimplexFiberPoint i x t) =
      q.c i + q.radial * t := by
  simp [euclideanRT0ComponentEval]

/-- A nonselected RT0 coordinate is constant along the `i`-th fiber. -/
theorem euclideanRT0ComponentEval_fiberPoint_ne
    {d : Nat} (q : RT0AffineND d)
    (i j : Fin d) (x : EuclideanDomain d) (t : ℝ) (hji : j ≠ i) :
    euclideanRT0ComponentEval q j (referenceSimplexFiberPoint i x t) =
      euclideanRT0ComponentEval q j x := by
  unfold euclideanRT0ComponentEval
  rw [referenceSimplexFiberPoint_proj_ne i j x t hji]

/-- Exact finite-difference formula for the selected RT0 coordinate along its fiber. -/
theorem euclideanRT0ComponentEval_fiberPoint_sub
    {d : Nat} (q : RT0AffineND d)
    (i : Fin d) (x : EuclideanDomain d) (s t : ℝ) :
    euclideanRT0ComponentEval q i (referenceSimplexFiberPoint i x t) -
        euclideanRT0ComponentEval q i (referenceSimplexFiberPoint i x s) =
      q.radial * (t - s) := by
  rw [euclideanRT0ComponentEval_fiberPoint_same,
    euclideanRT0ComponentEval_fiberPoint_same]
  ring

/-- The derivative of the selected RT0 coordinate along its fiber is the radial coefficient. -/
theorem euclideanRT0ComponentEval_fiberPoint_hasDerivAt
    {d : Nat} (q : RT0AffineND d)
    (i : Fin d) (x : EuclideanDomain d) (t : ℝ) :
    HasDerivAt
      (fun s => euclideanRT0ComponentEval q i
        (referenceSimplexFiberPoint i x s))
      q.radial t := by
  have hconst : HasDerivAt (fun _ : ℝ => q.c i) 0 t :=
    hasDerivAt_const t (q.c i)
  have hlinear :
      HasDerivAt (fun s : ℝ => q.radial * s) q.radial t :=
    hasDerivAt_const_mul (x := t) q.radial
  simpa [euclideanRT0ComponentEval_fiberPoint_same] using
    hconst.add hlinear

/--
A Schwartz test function restricted to the coordinate line has derivative equal
to its ambient directional derivative in the canonical basis direction.
-/
theorem schwartzMap_referenceSimplexFiber_hasDerivAt
    {d : Nat} (φ : 𝓢(EuclideanDomain d, ℂ))
    (i : Fin d) (x : EuclideanDomain d) (t : ℝ) :
    HasDerivAt
      (fun s => φ (referenceSimplexFiberPoint i x s))
      ((∂_{basisVector i} φ) (referenceSimplexFiberPoint i x t)) t := by
  have h :=
    (SchwartzMap.hasFDerivAt φ (referenceSimplexFiberPoint i x t))
      .comp_hasDerivAt t (referenceSimplexFiberPoint_hasDerivAt i x t)
  simpa [Function.comp_def, SchwartzMap.lineDerivOp_apply_eq_fderiv] using h

/-- The restricted directional derivative of a Schwartz function is continuous in the fiber parameter. -/
theorem schwartzMap_referenceSimplexFiber_lineDeriv_continuous
    {d : Nat} (φ : 𝓢(EuclideanDomain d, ℂ))
    (i : Fin d) (x : EuclideanDomain d) :
    Continuous
      (fun t =>
        (∂_{basisVector i} φ) (referenceSimplexFiberPoint i x t)) := by
  exact
    (SchwartzMap.continuous (∂_{basisVector i} φ)).comp
      (referenceSimplexFiberPoint_continuous i x)

/--
Exact interval integration by parts for a P1 coefficient against a Schwartz test
function along one coordinate fiber.
-/
theorem euclideanAffineScalarEval_fiber_integrationByParts
    {d : Nat} (u : AffineScalar d)
    (φ : 𝓢(EuclideanDomain d, ℂ))
    (i : Fin d) (x : EuclideanDomain d) (a b : ℝ) :
    (∫ t in a..b,
      euclideanAffineScalarEval u (referenceSimplexFiberPoint i x t) •
        (∂_{basisVector i} φ) (referenceSimplexFiberPoint i x t)) =
      euclideanAffineScalarEval u (referenceSimplexFiberPoint i x b) •
          φ (referenceSimplexFiberPoint i x b) -
        euclideanAffineScalarEval u (referenceSimplexFiberPoint i x a) •
          φ (referenceSimplexFiberPoint i x a) -
        ∫ t in a..b,
          u.grad i • φ (referenceSimplexFiberPoint i x t) := by
  apply intervalIntegral.integral_smul_deriv_eq_deriv_smul
  · intro t _
    exact euclideanAffineScalarEval_fiberPoint_hasDerivAt u i x t
  · intro t _
    exact schwartzMap_referenceSimplexFiber_hasDerivAt φ i x t
  · exact continuous_const.intervalIntegrable ..
  · exact
      (schwartzMap_referenceSimplexFiber_lineDeriv_continuous φ i x)
        .intervalIntegrable _ _

/--
Exact interval integration by parts for the selected RT0 coordinate against a
Schwartz test function.  The cellwise derivative contribution is the common
radial coefficient; summing over coordinates later gives `d * q.radial`.
-/
theorem euclideanRT0ComponentEval_fiber_integrationByParts
    {d : Nat} (q : RT0AffineND d)
    (φ : 𝓢(EuclideanDomain d, ℂ))
    (i : Fin d) (x : EuclideanDomain d) (a b : ℝ) :
    (∫ t in a..b,
      euclideanRT0ComponentEval q i (referenceSimplexFiberPoint i x t) •
        (∂_{basisVector i} φ) (referenceSimplexFiberPoint i x t)) =
      euclideanRT0ComponentEval q i (referenceSimplexFiberPoint i x b) •
          φ (referenceSimplexFiberPoint i x b) -
        euclideanRT0ComponentEval q i (referenceSimplexFiberPoint i x a) •
          φ (referenceSimplexFiberPoint i x a) -
        ∫ t in a..b,
          q.radial • φ (referenceSimplexFiberPoint i x t) := by
  apply intervalIntegral.integral_smul_deriv_eq_deriv_smul
  · intro t _
    exact euclideanRT0ComponentEval_fiberPoint_hasDerivAt q i x t
  · intro t _
    exact schwartzMap_referenceSimplexFiber_hasDerivAt φ i x t
  · exact continuous_const.intervalIntegrable ..
  · exact
      (schwartzMap_referenceSimplexFiber_lineDeriv_continuous φ i x)
        .intervalIntegrable _ _

end

end Continuum

end CACEFormal
