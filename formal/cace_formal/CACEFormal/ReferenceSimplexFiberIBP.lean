import Mathlib
import CACEFormal.ReferenceSimplexIntegrability

namespace CACEFormal

open Set MeasureTheory
open scoped BigOperators LineDeriv Interval SchwartzMap

namespace Continuum

noncomputable section

/-!
# Interval integration by parts on reference-simplex fibers

This module restores the analytic layer above the elementary affine fiber
calculus without modifying that shared calculus module.

For a fixed coordinate fiber:
* the fiber map is continuously differentiable with velocity `e_i`;
* a Schwartz test function restricted to the fiber has derivative equal to its
  ambient directional derivative in direction `e_i`;
* the P1 and RT0 affine restrictions satisfy exact one-dimensional integration
  by parts against the restricted Schwartz test.

These are the local one-dimensional identities that will be integrated over
the orthogonal base domain by the reference-simplex Fubini theorem.
-/

/-- The coordinate-fiber parameterization is continuous. -/
theorem referenceSimplexFiberPoint_continuous
    {d : Nat} (i : Fin d) (x : EuclideanDomain d) :
    Continuous (referenceSimplexFiberPoint i x) := by
  rw [continuous_iff_continuousAt]
  intro t
  exact (referenceSimplexFiberPoint_hasDerivAt i x t).continuousAt

/--
A Schwartz test function restricted to a coordinate fiber has derivative equal
to its ambient directional derivative in the basis direction.
-/
theorem schwartzMap_referenceSimplexFiber_hasDerivAt
    {d : Nat} (φ : 𝓢(EuclideanDomain d, ℂ))
    (i : Fin d) (x : EuclideanDomain d) (t : ℝ) :
    HasDerivAt
      (fun s => φ (referenceSimplexFiberPoint i x s))
      ((∂_{basisVector i} φ)
        (referenceSimplexFiberPoint i x t)) t := by
  have h :=
    (SchwartzMap.hasFDerivAt φ
      (referenceSimplexFiberPoint i x t))
      .comp_hasDerivAt t
        (referenceSimplexFiberPoint_hasDerivAt i x t)
  simpa [Function.comp_def,
    SchwartzMap.lineDerivOp_apply_eq_fderiv] using h

/-- The restricted Schwartz test is continuous along every coordinate fiber. -/
theorem schwartzMap_referenceSimplexFiber_continuous
    {d : Nat} (φ : 𝓢(EuclideanDomain d, ℂ))
    (i : Fin d) (x : EuclideanDomain d) :
    Continuous
      (fun t => φ (referenceSimplexFiberPoint i x t)) :=
  φ.continuous.comp (referenceSimplexFiberPoint_continuous i x)

/-- The restricted directional derivative is continuous along every coordinate fiber. -/
theorem schwartzMap_referenceSimplexFiber_lineDeriv_continuous
    {d : Nat} (φ : 𝓢(EuclideanDomain d, ℂ))
    (i : Fin d) (x : EuclideanDomain d) :
    Continuous
      (fun t =>
        (∂_{basisVector i} φ)
          (referenceSimplexFiberPoint i x t)) :=
  (SchwartzMap.continuous (∂_{basisVector i} φ)).comp
    (referenceSimplexFiberPoint_continuous i x)

/--
Exact interval integration by parts for a P1 coefficient against a Schwartz
test function along one coordinate fiber.
-/
theorem referenceSimplexP1Fiber_integrationByParts
    {d : Nat} (u : AffineScalar d)
    (φ : 𝓢(EuclideanDomain d, ℂ))
    (i : Fin d) (x : EuclideanDomain d) (a b : ℝ) :
    (∫ t in a..b,
      referenceSimplexP1Fiber u i x t •
        (∂_{basisVector i} φ)
          (referenceSimplexFiberPoint i x t)) =
      referenceSimplexP1Fiber u i x b •
          φ (referenceSimplexFiberPoint i x b) -
        referenceSimplexP1Fiber u i x a •
          φ (referenceSimplexFiberPoint i x a) -
        ∫ t in a..b,
          u.grad i •
            φ (referenceSimplexFiberPoint i x t) := by
  apply intervalIntegral.integral_smul_deriv_eq_deriv_smul
  · intro t _
    exact referenceSimplexP1Fiber_hasDerivAt u i x t
  · intro t _
    exact schwartzMap_referenceSimplexFiber_hasDerivAt φ i x t
  · exact continuous_const.intervalIntegrable ..
  · exact
      (schwartzMap_referenceSimplexFiber_lineDeriv_continuous φ i x)
        .intervalIntegrable _ _

/--
Exact interval integration by parts for the selected RT0 coordinate against a
Schwartz test function.  The derivative contribution is the common radial
coefficient.
-/
theorem referenceSimplexRT0Fiber_integrationByParts
    {d : Nat} (q : RT0AffineND d)
    (φ : 𝓢(EuclideanDomain d, ℂ))
    (i : Fin d) (x : EuclideanDomain d) (a b : ℝ) :
    (∫ t in a..b,
      referenceSimplexRT0Fiber q i x t •
        (∂_{basisVector i} φ)
          (referenceSimplexFiberPoint i x t)) =
      referenceSimplexRT0Fiber q i x b •
          φ (referenceSimplexFiberPoint i x b) -
        referenceSimplexRT0Fiber q i x a •
          φ (referenceSimplexFiberPoint i x a) -
        ∫ t in a..b,
          q.radial •
            φ (referenceSimplexFiberPoint i x t) := by
  apply intervalIntegral.integral_smul_deriv_eq_deriv_smul
  · intro t _
    exact referenceSimplexRT0Fiber_hasDerivAt q i x t
  · intro t _
    exact schwartzMap_referenceSimplexFiber_hasDerivAt φ i x t
  · exact continuous_const.intervalIntegrable ..
  · exact
      (schwartzMap_referenceSimplexFiber_lineDeriv_continuous φ i x)
        .intervalIntegrable _ _

end

end Continuum

end CACEFormal
