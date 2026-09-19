import Mathlib
import CACEFormal.SimplexCellDistributionBridge

namespace CACEFormal

open Set MeasureTheory
open scoped BigOperators LineDeriv SchwartzMap

namespace Continuum

noncomputable section

/-!
# Concrete evaluation of real L² simplex distributions

This module exposes the integral semantics already present in the
`realL2ScalarDistribution` definition.  It is an interface layer between the
L² graph coordinates and the explicit Gauss--Green integrals.

No new analytic assumption is introduced: the proofs only unfold the canonical
L²-to-tempered-distribution embedding and use the a.e. representatives of the
simplex L² objects.
-/

/-- A real L² field, complexified and embedded as a tempered distribution, acts by the expected integral. -/
theorem realL2ScalarDistribution_apply
    {d : Nat} (u : RealL2 d)
    (φ : 𝓢(EuclideanDomain d, ℂ)) :
    realL2ScalarDistribution d u φ =
      ∫ x, φ x * Complex.ofReal (u x) := by
  change
    MeasureTheory.Lp.toTemperedDistribution
        (realL2ToComplexL2 d u) φ =
      ∫ x, φ x * Complex.ofReal (u x)
  rw [MeasureTheory.Lp.toTemperedDistribution_apply]
  apply integral_congr_ae
  filter_upwards
    [ContinuousLinearMap.coeFn_compLpL Complex.ofRealCLM u] with x hx
  rw [hx]
  simp [Algebra.smul_def]

/-- P1 value distribution acts as the integral of the simplex-supported affine value. -/
theorem geometricSimplexP1ValueDistribution_apply
    {d : Nat} (s : GeometricSimplex d) (u : AffineScalar d)
    (φ : 𝓢(EuclideanDomain d, ℂ)) :
    geometricSimplexP1ValueDistribution s u φ =
      ∫ x,
        φ x *
          Complex.ofReal
            ((euclideanSimplexSet s.points).indicator
              (euclideanAffineScalarEval u) x) := by
  rw [geometricSimplexP1ValueDistribution, realL2ScalarDistribution_apply]
  apply integral_congr_ae
  filter_upwards [euclideanSimplexScalarL2_coeFn_ae s.points u] with x hx
  rw [hx]

/-- P1 gradient-coordinate distribution acts as the corresponding constant simplex indicator. -/
theorem geometricSimplexP1GradientDistribution_apply
    {d : Nat} (s : GeometricSimplex d) (u : AffineScalar d)
    (i : Fin d) (φ : 𝓢(EuclideanDomain d, ℂ)) :
    geometricSimplexP1GradientDistribution s u i φ =
      ∫ x,
        φ x *
          Complex.ofReal
            ((euclideanSimplexSet s.points).indicator
              (fun _ => u.grad i) x) := by
  rw [geometricSimplexP1GradientDistribution, realL2ScalarDistribution_apply]
  apply integral_congr_ae
  filter_upwards [euclideanSimplexGradL2_coeFn_ae s.points u i] with x hx
  rw [hx]

/-- RT0 component distribution acts as the simplex-supported coordinate integral. -/
theorem geometricSimplexRT0FieldDistribution_apply
    {d : Nat} (s : GeometricSimplex d) (q : RT0AffineND d)
    (i : Fin d) (φ : 𝓢(EuclideanDomain d, ℂ)) :
    geometricSimplexRT0FieldDistribution s q i φ =
      ∫ x,
        φ x *
          Complex.ofReal
            ((euclideanSimplexSet s.points).indicator
              (euclideanRT0ComponentEval q i) x) := by
  rw [geometricSimplexRT0FieldDistribution, realL2ScalarDistribution_apply]
  apply integral_congr_ae
  filter_upwards [euclideanSimplexRT0ComponentL2_coeFn_ae s.points q i] with x hx
  rw [hx]

/-- RT0 divergence distribution acts as the constant divergence simplex indicator. -/
theorem geometricSimplexRT0DivergenceDistribution_apply
    {d : Nat} (s : GeometricSimplex d) (q : RT0AffineND d)
    (φ : 𝓢(EuclideanDomain d, ℂ)) :
    geometricSimplexRT0DivergenceDistribution s q φ =
      ∫ x,
        φ x *
          Complex.ofReal
            ((euclideanSimplexSet s.points).indicator
              (fun _ => q.divergence) x) := by
  rw [geometricSimplexRT0DivergenceDistribution, realL2ScalarDistribution_apply]
  apply integral_congr_ae
  filter_upwards [euclideanSimplexDivL2_coeFn_ae s.points q] with x hx
  rw [hx]

end

end Continuum

end CACEFormal
