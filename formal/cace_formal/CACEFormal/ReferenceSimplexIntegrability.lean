import Mathlib
import CACEFormal.ReferenceSimplexFubini
import CACEFormal.SimplexFacetCurrent

namespace CACEFormal

open Set MeasureTheory
open scoped BigOperators MeasureTheory LineDeriv SchwartzMap

namespace Continuum

noncomputable section

/-!
# Measurability and integrability for reference-simplex Gauss--Green

This module discharges the routine analytic hypotheses needed to specialize the
fiberwise Fubini theorem to P1/RT0 coefficients against Schwartz test functions.

The affine coefficients have temperate growth. After complexification,
multiplying them by a Schwartz test function produces another Schwartz
function, hence an integrable function. Restriction to the closed reference
simplex preserves integrability, and the measure-preserving orthogonal
coordinate change preserves it again.
-/

/-- The reference simplex is an intersection of closed coordinate halfspaces and one sum halfspace. -/
theorem euclideanReferenceSimplex_eq_inter (d : Nat) :
    euclideanReferenceSimplex d =
      (⋂ j : Fin d,
        {x : EuclideanDomain d | 0 ≤ EuclideanSpace.proj j x}) ∩
      {x : EuclideanDomain d |
        (∑ j : Fin d, EuclideanSpace.proj j x) ≤ 1} := by
  ext x
  simp [euclideanReferenceSimplex]

/-- The Euclidean reference simplex is closed. -/
theorem euclideanReferenceSimplex_isClosed (d : Nat) :
    IsClosed (euclideanReferenceSimplex d) := by
  rw [euclideanReferenceSimplex_eq_inter]
  apply IsClosed.inter
  · apply isClosed_iInter
    intro j
    exact isClosed_le continuous_const (by fun_prop)
  · exact isClosed_le (by fun_prop) continuous_const

/-- The Euclidean reference simplex is measurable. -/
theorem euclideanReferenceSimplex_measurableSet (d : Nat) :
    MeasurableSet (euclideanReferenceSimplex d) :=
  (euclideanReferenceSimplex_isClosed d).measurableSet

/-- Complexification of the affine P1 coefficient on the canonical Euclidean ambient. -/
def complexEuclideanAffineScalarEval {d : Nat}
    (u : AffineScalar d) (x : EuclideanDomain d) : ℂ :=
  Complex.ofReal (euclideanAffineScalarEval u x)

/-- Complexified affine P1 coefficients retain temperate growth. -/
theorem complexEuclideanAffineScalarEval_hasTemperateGrowth
    {d : Nat} (u : AffineScalar d) :
    Function.HasTemperateGrowth (complexEuclideanAffineScalarEval u) := by
  exact Complex.hasTemperateGrowth_ofReal.comp
    (euclideanAffineScalarEval_hasTemperateGrowth u)

/-- Complexification of one RT0 coordinate. -/
def complexEuclideanRT0ComponentEval {d : Nat}
    (q : RT0AffineND d) (i : Fin d) (x : EuclideanDomain d) : ℂ :=
  Complex.ofReal (euclideanRT0ComponentEval q i x)

/-- Complexified RT0 coordinates retain temperate growth. -/
theorem complexEuclideanRT0ComponentEval_hasTemperateGrowth
    {d : Nat} (q : RT0AffineND d) (i : Fin d) :
    Function.HasTemperateGrowth (complexEuclideanRT0ComponentEval q i) := by
  exact Complex.hasTemperateGrowth_ofReal.comp
    (euclideanRT0ComponentEval_hasTemperateGrowth q i)

/-- A complexified affine P1 coefficient times any Schwartz test function is integrable. -/
theorem complexEuclideanAffineScalarEval_smul_schwartz_integrable
    {d : Nat} (u : AffineScalar d)
    (φ : 𝓢(EuclideanDomain d, ℂ)) :
    Integrable
      (fun x =>
        complexEuclideanAffineScalarEval u x • φ x) := by
  have hg :=
    complexEuclideanAffineScalarEval_hasTemperateGrowth u
  have h :=
    (SchwartzMap.smulLeftCLM ℂ
      (complexEuclideanAffineScalarEval u) φ).integrable volume
  rw [SchwartzMap.smulLeftCLM_apply hg] at h
  exact h

/-- A complexified RT0 coordinate times any Schwartz test function is integrable. -/
theorem complexEuclideanRT0ComponentEval_smul_schwartz_integrable
    {d : Nat} (q : RT0AffineND d) (i : Fin d)
    (φ : 𝓢(EuclideanDomain d, ℂ)) :
    Integrable
      (fun x =>
        complexEuclideanRT0ComponentEval q i x • φ x) := by
  have hg :=
    complexEuclideanRT0ComponentEval_hasTemperateGrowth q i
  have h :=
    (SchwartzMap.smulLeftCLM ℂ
      (complexEuclideanRT0ComponentEval q i) φ).integrable volume
  rw [SchwartzMap.smulLeftCLM_apply hg] at h
  exact h

/--
The real affine P1 coefficient acting by real scalar multiplication on a complex
Schwartz test function is integrable.  This is the exact scalar action used by
the fiberwise integration-by-parts theorem.
-/
theorem euclideanAffineScalarEval_smul_schwartz_integrable
    {d : Nat} (u : AffineScalar d)
    (φ : 𝓢(EuclideanDomain d, ℂ)) :
    Integrable
      (fun x =>
        euclideanAffineScalarEval u x • φ x) := by
  have hg := euclideanAffineScalarEval_hasTemperateGrowth u
  have h :=
    (SchwartzMap.smulLeftCLM ℂ
      (euclideanAffineScalarEval u) φ).integrable volume
  rw [SchwartzMap.smulLeftCLM_apply hg] at h
  exact h

/--
The real RT0 coordinate acting by real scalar multiplication on a complex
Schwartz test function is integrable.
-/
theorem euclideanRT0ComponentEval_smul_schwartz_integrable
    {d : Nat} (q : RT0AffineND d) (i : Fin d)
    (φ : 𝓢(EuclideanDomain d, ℂ)) :
    Integrable
      (fun x =>
        euclideanRT0ComponentEval q i x • φ x) := by
  have hg := euclideanRT0ComponentEval_hasTemperateGrowth q i
  have h :=
    (SchwartzMap.smulLeftCLM ℂ
      (euclideanRT0ComponentEval q i) φ).integrable volume
  rw [SchwartzMap.smulLeftCLM_apply hg] at h
  exact h

/-- A constant real scalar times a complex Schwartz test is integrable. -/
theorem realConst_smul_schwartz_integrable
    {d : Nat} (c : ℝ)
    (φ : 𝓢(EuclideanDomain d, ℂ)) :
    Integrable (fun x => c • φ x) := by
  exact φ.integrable.const_smul c

/-- The P1-Schwartz product remains integrable after restriction to the reference simplex. -/
theorem referenceSimplex_complexAffine_smul_schwartz_integrable
    {d : Nat} (u : AffineScalar d)
    (φ : 𝓢(EuclideanDomain d, ℂ)) :
    Integrable
      ((euclideanReferenceSimplex d).indicator
        (fun x =>
          complexEuclideanAffineScalarEval u x • φ x)) := by
  exact
    (complexEuclideanAffineScalarEval_smul_schwartz_integrable u φ).indicator
      (euclideanReferenceSimplex_measurableSet d)

/-- The RT0-Schwartz product remains integrable after restriction to the reference simplex. -/
theorem referenceSimplex_complexRT0_smul_schwartz_integrable
    {d : Nat} (q : RT0AffineND d) (i : Fin d)
    (φ : 𝓢(EuclideanDomain d, ℂ)) :
    Integrable
      ((euclideanReferenceSimplex d).indicator
        (fun x =>
          complexEuclideanRT0ComponentEval q i x • φ x)) := by
  exact
    (complexEuclideanRT0ComponentEval_smul_schwartz_integrable q i φ).indicator
      (euclideanReferenceSimplex_measurableSet d)

/-- The exact real-scalar P1-Schwartz integrand is integrable on the reference simplex. -/
theorem referenceSimplex_affine_smul_schwartz_integrable
    {d : Nat} (u : AffineScalar d)
    (φ : 𝓢(EuclideanDomain d, ℂ)) :
    Integrable
      ((euclideanReferenceSimplex d).indicator
        (fun x => euclideanAffineScalarEval u x • φ x)) := by
  exact
    (euclideanAffineScalarEval_smul_schwartz_integrable u φ).indicator
      (euclideanReferenceSimplex_measurableSet d)

/-- The exact real-scalar RT0-Schwartz integrand is integrable on the reference simplex. -/
theorem referenceSimplex_RT0_smul_schwartz_integrable
    {d : Nat} (q : RT0AffineND d) (i : Fin d)
    (φ : 𝓢(EuclideanDomain d, ℂ)) :
    Integrable
      ((euclideanReferenceSimplex d).indicator
        (fun x => euclideanRT0ComponentEval q i x • φ x)) := by
  exact
    (euclideanRT0ComponentEval_smul_schwartz_integrable q i φ).indicator
      (euclideanReferenceSimplex_measurableSet d)

/-- A constant-gradient Schwartz integrand is integrable on the reference simplex. -/
theorem referenceSimplex_realConst_smul_schwartz_integrable
    {d : Nat} (c : ℝ)
    (φ : 𝓢(EuclideanDomain d, ℂ)) :
    Integrable
      ((euclideanReferenceSimplex d).indicator
        (fun x => c • φ x)) := by
  exact
    (realConst_smul_schwartz_integrable c φ).indicator
      (euclideanReferenceSimplex_measurableSet d)

/-- Product-coordinate integrability for the exact real-scalar P1-Schwartz integrand. -/
theorem referenceSimplex_affine_fiberCoordinates_integrable
    {d : Nat} (u : AffineScalar d)
    (φ : 𝓢(EuclideanDomain d, ℂ)) (i : Fin d) :
    Integrable
      (fun q :
        referenceSimplexCoordinateLine i ×
          (referenceSimplexCoordinateLine i)ᗮ =>
        (euclideanReferenceSimplex d).indicator
          (fun x => euclideanAffineScalarEval u x • φ x)
          ((q.1 : EuclideanDomain d) + (q.2 : EuclideanDomain d))) := by
  exact
    (referenceSimplex_affine_smul_schwartz_integrable u φ)
      .coordinateLine_prod i

/-- Product-coordinate integrability for one exact real-scalar RT0-Schwartz integrand. -/
theorem referenceSimplex_RT0_fiberCoordinates_integrable
    {d : Nat} (q : RT0AffineND d) (i : Fin d)
    (φ : 𝓢(EuclideanDomain d, ℂ)) :
    Integrable
      (fun p :
        referenceSimplexCoordinateLine i ×
          (referenceSimplexCoordinateLine i)ᗮ =>
        (euclideanReferenceSimplex d).indicator
          (fun x => euclideanRT0ComponentEval q i x • φ x)
          ((p.1 : EuclideanDomain d) + (p.2 : EuclideanDomain d))) := by
  exact
    (referenceSimplex_RT0_smul_schwartz_integrable q i φ)
      .coordinateLine_prod i

/-- Product-coordinate integrability for a constant real scalar times a Schwartz test. -/
theorem referenceSimplex_realConst_fiberCoordinates_integrable
    {d : Nat} (c : ℝ)
    (φ : 𝓢(EuclideanDomain d, ℂ)) (i : Fin d) :
    Integrable
      (fun p :
        referenceSimplexCoordinateLine i ×
          (referenceSimplexCoordinateLine i)ᗮ =>
        (euclideanReferenceSimplex d).indicator
          (fun x => c • φ x)
          ((p.1 : EuclideanDomain d) + (p.2 : EuclideanDomain d))) := by
  exact
    (referenceSimplex_realConst_smul_schwartz_integrable c φ)
      .coordinateLine_prod i

/--
The transformed integrability hypothesis required by reference-simplex Fubini
for a P1 coefficient times a Schwartz function.
-/
theorem referenceSimplex_complexAffine_fiberCoordinates_integrable
    {d : Nat} (u : AffineScalar d)
    (φ : 𝓢(EuclideanDomain d, ℂ)) (i : Fin d) :
    Integrable
      (fun q :
        referenceSimplexCoordinateLine i ×
          (referenceSimplexCoordinateLine i)ᗮ =>
        (euclideanReferenceSimplex d).indicator
          (fun x =>
            complexEuclideanAffineScalarEval u x • φ x)
          ((q.1 : EuclideanDomain d) + (q.2 : EuclideanDomain d))) := by
  exact
    (referenceSimplex_complexAffine_smul_schwartz_integrable u φ)
      .coordinateLine_prod i

/--
The transformed integrability hypothesis required by reference-simplex Fubini
for one RT0 coordinate times a Schwartz function.
-/
theorem referenceSimplex_complexRT0_fiberCoordinates_integrable
    {d : Nat} (q : RT0AffineND d) (i : Fin d)
    (φ : 𝓢(EuclideanDomain d, ℂ)) :
    Integrable
      (fun p :
        referenceSimplexCoordinateLine i ×
          (referenceSimplexCoordinateLine i)ᗮ =>
        (euclideanReferenceSimplex d).indicator
          (fun x =>
            complexEuclideanRT0ComponentEval q i x • φ x)
          ((p.1 : EuclideanDomain d) + (p.2 : EuclideanDomain d))) := by
  exact
    (referenceSimplex_complexRT0_smul_schwartz_integrable q i φ)
      .coordinateLine_prod i

end

end Continuum

end CACEFormal
