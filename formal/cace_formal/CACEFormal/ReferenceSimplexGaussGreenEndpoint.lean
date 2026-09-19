import Mathlib
import CACEFormal.ReferenceSimplexEndpointIBP
import CACEFormal.ReferenceSimplexIntegrability
import CACEFormal.ReferenceSimplexFubini

namespace CACEFormal

open Set MeasureTheory
open scoped BigOperators LineDeriv

namespace Continuum

noncomputable section

/-!
# Reference-simplex Gauss--Green with explicit endpoint boundary form

This is the first full local integration-by-parts theorem on the reference
simplex.  The boundary is still represented by its exact coordinate-fiber
endpoint integral:

  boundary = upper endpoint - lower endpoint.

The remaining geometric-measure theorem will identify this endpoint form with
the already-defined Hausdorff facet-current distribution.
-/

/-- P1 fiber derivative contribution, already restricted to the admissible base domain. -/
def referenceSimplexP1DerivativeBase
    {d : Nat} (u : AffineScalar d)
    (φ : 𝓢(EuclideanDomain d, ℂ)) (i : Fin d) :
    (referenceSimplexCoordinateLine i)ᗮ → ℂ :=
  (referenceSimplexFiberBaseDomain i).indicator
    (fun y =>
      ∫ t in
        Set.Icc 0
          (referenceSimplexFiberUpper i (y : EuclideanDomain d)),
        euclideanAffineScalarEval u
            (referenceSimplexFiberPoint i (y : EuclideanDomain d) t) •
          (∂_{basisVector i} φ)
            (referenceSimplexFiberPoint i (y : EuclideanDomain d) t))

/-- P1 fiber interior derivative term. -/
def referenceSimplexP1InteriorBase
    {d : Nat} (u : AffineScalar d)
    (φ : 𝓢(EuclideanDomain d, ℂ)) (i : Fin d) :
    (referenceSimplexCoordinateLine i)ᗮ → ℂ :=
  (referenceSimplexFiberBaseDomain i).indicator
    (fun y =>
      ∫ t in
        Set.Icc 0
          (referenceSimplexFiberUpper i (y : EuclideanDomain d)),
        u.grad i •
          φ (referenceSimplexFiberPoint i (y : EuclideanDomain d) t))

/-- P1 oriented boundary endpoint term: top minus coordinate-face endpoint. -/
def referenceSimplexP1BoundaryBase
    {d : Nat} (u : AffineScalar d)
    (φ : 𝓢(EuclideanDomain d, ℂ)) (i : Fin d) :
    (referenceSimplexCoordinateLine i)ᗮ → ℂ :=
  (referenceSimplexFiberBaseDomain i).indicator
    (fun y =>
      euclideanAffineScalarEval u
          (referenceSimplexFiberPoint i (y : EuclideanDomain d)
            (referenceSimplexFiberUpper i (y : EuclideanDomain d))) •
        φ (referenceSimplexFiberPoint i (y : EuclideanDomain d)
          (referenceSimplexFiberUpper i (y : EuclideanDomain d))) -
      euclideanAffineScalarEval u
          (referenceSimplexFiberPoint i (y : EuclideanDomain d) 0) •
        φ (referenceSimplexFiberPoint i (y : EuclideanDomain d) 0))

/-- Pointwise P1 Gauss--Green on the orthogonal base domain. -/
theorem referenceSimplexP1_base_gaussGreen
    {d : Nat} (u : AffineScalar d)
    (φ : 𝓢(EuclideanDomain d, ℂ)) (i : Fin d)
    (y : (referenceSimplexCoordinateLine i)ᗮ) :
    -referenceSimplexP1DerivativeBase u φ i y =
      referenceSimplexP1InteriorBase u φ i y -
        referenceSimplexP1BoundaryBase u φ i y := by
  by_cases hy : y ∈ referenceSimplexFiberBaseDomain i
  · simp only [referenceSimplexP1DerivativeBase,
      referenceSimplexP1InteriorBase, referenceSimplexP1BoundaryBase,
      Set.indicator_of_mem hy]
    have h :=
      referenceSimplexP1_fiber_setIntegral_ibp u φ i y hy
    calc
      -(∫ t in
          Set.Icc 0
            (referenceSimplexFiberUpper i (y : EuclideanDomain d)),
          euclideanAffineScalarEval u
              (referenceSimplexFiberPoint i (y : EuclideanDomain d) t) •
            (∂_{basisVector i} φ)
              (referenceSimplexFiberPoint i (y : EuclideanDomain d) t)) =
          (∫ t in
            Set.Icc 0
              (referenceSimplexFiberUpper i (y : EuclideanDomain d)),
            u.grad i •
              φ (referenceSimplexFiberPoint i (y : EuclideanDomain d) t)) +
          euclideanAffineScalarEval u
              (referenceSimplexFiberPoint i (y : EuclideanDomain d) 0) •
            φ (referenceSimplexFiberPoint i (y : EuclideanDomain d) 0) -
          euclideanAffineScalarEval u
              (referenceSimplexFiberPoint i (y : EuclideanDomain d)
                (referenceSimplexFiberUpper i (y : EuclideanDomain d))) •
            φ (referenceSimplexFiberPoint i (y : EuclideanDomain d)
              (referenceSimplexFiberUpper i (y : EuclideanDomain d))) := h
      _ =
          (∫ t in
            Set.Icc 0
              (referenceSimplexFiberUpper i (y : EuclideanDomain d)),
            u.grad i •
              φ (referenceSimplexFiberPoint i (y : EuclideanDomain d) t)) -
          (euclideanAffineScalarEval u
              (referenceSimplexFiberPoint i (y : EuclideanDomain d)
                (referenceSimplexFiberUpper i (y : EuclideanDomain d))) •
            φ (referenceSimplexFiberPoint i (y : EuclideanDomain d)
              (referenceSimplexFiberUpper i (y : EuclideanDomain d))) -
           euclideanAffineScalarEval u
              (referenceSimplexFiberPoint i (y : EuclideanDomain d) 0) •
            φ (referenceSimplexFiberPoint i (y : EuclideanDomain d) 0)) := by
        abel
  · simp [referenceSimplexP1DerivativeBase,
      referenceSimplexP1InteriorBase, referenceSimplexP1BoundaryBase,
      Set.indicator_of_notMem hy]

/-- The P1 derivative base function is integrable. -/
theorem referenceSimplexP1DerivativeBase_integrable
    {d : Nat} (u : AffineScalar d)
    (φ : 𝓢(EuclideanDomain d, ℂ)) (i : Fin d) :
    Integrable (referenceSimplexP1DerivativeBase u φ i) := by
  simpa [referenceSimplexP1DerivativeBase] using
    (integrable_referenceSimplex_fiberIntegral
      i
      (fun x =>
        euclideanAffineScalarEval u x •
          (∂_{basisVector i} φ) x)
      (referenceSimplex_affine_fiberCoordinates_integrable
        u (∂_{basisVector i} φ) i))

/-- The P1 interior base function is integrable. -/
theorem referenceSimplexP1InteriorBase_integrable
    {d : Nat} (u : AffineScalar d)
    (φ : 𝓢(EuclideanDomain d, ℂ)) (i : Fin d) :
    Integrable (referenceSimplexP1InteriorBase u φ i) := by
  simpa [referenceSimplexP1InteriorBase] using
    (integrable_referenceSimplex_fiberIntegral
      i
      (fun x => u.grad i • φ x)
      (referenceSimplex_realConst_fiberCoordinates_integrable
        (u.grad i) φ i))

/-- The explicit P1 endpoint boundary base function is integrable. -/
theorem referenceSimplexP1BoundaryBase_integrable
    {d : Nat} (u : AffineScalar d)
    (φ : 𝓢(EuclideanDomain d, ℂ)) (i : Fin d) :
    Integrable (referenceSimplexP1BoundaryBase u φ i) := by
  have hD := referenceSimplexP1DerivativeBase_integrable u φ i
  have hI := referenceSimplexP1InteriorBase_integrable u φ i
  have heq :
      referenceSimplexP1BoundaryBase u φ i =
        referenceSimplexP1InteriorBase u φ i +
          referenceSimplexP1DerivativeBase u φ i := by
    funext y
    have h := referenceSimplexP1_base_gaussGreen u φ i y
    linear_combination h
  rw [heq]
  exact hI.add hD

/-- The explicit oriented P1 endpoint boundary functional. -/
def referenceSimplexP1EndpointBoundary
    {d : Nat} (u : AffineScalar d)
    (φ : 𝓢(EuclideanDomain d, ℂ)) (i : Fin d) : ℂ :=
  ∫ y : (referenceSimplexCoordinateLine i)ᗮ,
    referenceSimplexP1BoundaryBase u φ i y

/--
Full reference-simplex P1 Gauss--Green identity with explicit endpoint boundary.

The boundary sign agrees with
`partial_i (u 1_Δ) = (partial_i u) 1_Δ - boundary_i`.
-/
theorem referenceSimplexP1_gaussGreen_endpoint
    {d : Nat} (u : AffineScalar d)
    (φ : 𝓢(EuclideanDomain d, ℂ)) (i : Fin d) :
    -(∫ x,
      (euclideanReferenceSimplex d).indicator
        (fun x =>
          euclideanAffineScalarEval u x •
            (∂_{basisVector i} φ) x) x) =
      (∫ x,
        (euclideanReferenceSimplex d).indicator
          (fun x => u.grad i • φ x) x) -
        referenceSimplexP1EndpointBoundary u φ i := by
  have hD :=
    integral_referenceSimplex_indicator_eq_fibers
      i
      (fun x =>
        euclideanAffineScalarEval u x •
          (∂_{basisVector i} φ) x)
      (referenceSimplex_affine_fiberCoordinates_integrable
        u (∂_{basisVector i} φ) i)
  have hI :=
    integral_referenceSimplex_indicator_eq_fibers
      i
      (fun x => u.grad i • φ x)
      (referenceSimplex_realConst_fiberCoordinates_integrable
        (u.grad i) φ i)
  rw [hD, hI, referenceSimplexP1EndpointBoundary]
  rw [← integral_neg]
  calc
    (∫ y : (referenceSimplexCoordinateLine i)ᗮ,
      -referenceSimplexP1DerivativeBase u φ i y) =
        ∫ y : (referenceSimplexCoordinateLine i)ᗮ,
          (referenceSimplexP1InteriorBase u φ i y -
            referenceSimplexP1BoundaryBase u φ i y) := by
      apply integral_congr_ae
      filter_upwards with y
      exact referenceSimplexP1_base_gaussGreen u φ i y
    _ =
        (∫ y : (referenceSimplexCoordinateLine i)ᗮ,
          referenceSimplexP1InteriorBase u φ i y) -
        ∫ y : (referenceSimplexCoordinateLine i)ᗮ,
          referenceSimplexP1BoundaryBase u φ i y := by
      rw [integral_sub
        (referenceSimplexP1InteriorBase_integrable u φ i)
        (referenceSimplexP1BoundaryBase_integrable u φ i)]

/-- RT0 coordinate fiber derivative contribution. -/
def referenceSimplexRT0DerivativeBase
    {d : Nat} (q : RT0AffineND d)
    (φ : 𝓢(EuclideanDomain d, ℂ)) (i : Fin d) :
    (referenceSimplexCoordinateLine i)ᗮ → ℂ :=
  (referenceSimplexFiberBaseDomain i).indicator
    (fun y =>
      ∫ t in
        Set.Icc 0
          (referenceSimplexFiberUpper i (y : EuclideanDomain d)),
        euclideanRT0ComponentEval q i
            (referenceSimplexFiberPoint i (y : EuclideanDomain d) t) •
          (∂_{basisVector i} φ)
            (referenceSimplexFiberPoint i (y : EuclideanDomain d) t))

/-- RT0 radial interior contribution on one coordinate fiber. -/
def referenceSimplexRT0InteriorBase
    {d : Nat} (q : RT0AffineND d)
    (φ : 𝓢(EuclideanDomain d, ℂ)) (i : Fin d) :
    (referenceSimplexCoordinateLine i)ᗮ → ℂ :=
  (referenceSimplexFiberBaseDomain i).indicator
    (fun y =>
      ∫ t in
        Set.Icc 0
          (referenceSimplexFiberUpper i (y : EuclideanDomain d)),
        q.radial •
          φ (referenceSimplexFiberPoint i (y : EuclideanDomain d) t))

/-- RT0 oriented endpoint boundary contribution for coordinate `i`. -/
def referenceSimplexRT0BoundaryBase
    {d : Nat} (q : RT0AffineND d)
    (φ : 𝓢(EuclideanDomain d, ℂ)) (i : Fin d) :
    (referenceSimplexCoordinateLine i)ᗮ → ℂ :=
  (referenceSimplexFiberBaseDomain i).indicator
    (fun y =>
      euclideanRT0ComponentEval q i
          (referenceSimplexFiberPoint i (y : EuclideanDomain d)
            (referenceSimplexFiberUpper i (y : EuclideanDomain d))) •
        φ (referenceSimplexFiberPoint i (y : EuclideanDomain d)
          (referenceSimplexFiberUpper i (y : EuclideanDomain d))) -
      euclideanRT0ComponentEval q i
          (referenceSimplexFiberPoint i (y : EuclideanDomain d) 0) •
        φ (referenceSimplexFiberPoint i (y : EuclideanDomain d) 0))

/-- Pointwise RT0 coordinate Gauss--Green on the orthogonal base domain. -/
theorem referenceSimplexRT0_base_gaussGreen
    {d : Nat} (q : RT0AffineND d)
    (φ : 𝓢(EuclideanDomain d, ℂ)) (i : Fin d)
    (y : (referenceSimplexCoordinateLine i)ᗮ) :
    -referenceSimplexRT0DerivativeBase q φ i y =
      referenceSimplexRT0InteriorBase q φ i y -
        referenceSimplexRT0BoundaryBase q φ i y := by
  by_cases hy : y ∈ referenceSimplexFiberBaseDomain i
  · simp only [referenceSimplexRT0DerivativeBase,
      referenceSimplexRT0InteriorBase, referenceSimplexRT0BoundaryBase,
      Set.indicator_of_mem hy]
    have h :=
      referenceSimplexRT0_fiber_setIntegral_ibp q φ i y hy
    calc
      -(∫ t in
          Set.Icc 0
            (referenceSimplexFiberUpper i (y : EuclideanDomain d)),
          euclideanRT0ComponentEval q i
              (referenceSimplexFiberPoint i (y : EuclideanDomain d) t) •
            (∂_{basisVector i} φ)
              (referenceSimplexFiberPoint i (y : EuclideanDomain d) t)) =
          (∫ t in
            Set.Icc 0
              (referenceSimplexFiberUpper i (y : EuclideanDomain d)),
            q.radial •
              φ (referenceSimplexFiberPoint i (y : EuclideanDomain d) t)) +
          euclideanRT0ComponentEval q i
              (referenceSimplexFiberPoint i (y : EuclideanDomain d) 0) •
            φ (referenceSimplexFiberPoint i (y : EuclideanDomain d) 0) -
          euclideanRT0ComponentEval q i
              (referenceSimplexFiberPoint i (y : EuclideanDomain d)
                (referenceSimplexFiberUpper i (y : EuclideanDomain d))) •
            φ (referenceSimplexFiberPoint i (y : EuclideanDomain d)
              (referenceSimplexFiberUpper i (y : EuclideanDomain d))) := h
      _ =
          (∫ t in
            Set.Icc 0
              (referenceSimplexFiberUpper i (y : EuclideanDomain d)),
            q.radial •
              φ (referenceSimplexFiberPoint i (y : EuclideanDomain d) t)) -
          (euclideanRT0ComponentEval q i
              (referenceSimplexFiberPoint i (y : EuclideanDomain d)
                (referenceSimplexFiberUpper i (y : EuclideanDomain d))) •
            φ (referenceSimplexFiberPoint i (y : EuclideanDomain d)
              (referenceSimplexFiberUpper i (y : EuclideanDomain d))) -
           euclideanRT0ComponentEval q i
              (referenceSimplexFiberPoint i (y : EuclideanDomain d) 0) •
            φ (referenceSimplexFiberPoint i (y : EuclideanDomain d) 0)) := by
        abel
  · simp [referenceSimplexRT0DerivativeBase,
      referenceSimplexRT0InteriorBase, referenceSimplexRT0BoundaryBase,
      Set.indicator_of_notMem hy]

/-- The RT0 derivative base function is integrable. -/
theorem referenceSimplexRT0DerivativeBase_integrable
    {d : Nat} (q : RT0AffineND d)
    (φ : 𝓢(EuclideanDomain d, ℂ)) (i : Fin d) :
    Integrable (referenceSimplexRT0DerivativeBase q φ i) := by
  simpa [referenceSimplexRT0DerivativeBase] using
    (integrable_referenceSimplex_fiberIntegral
      i
      (fun x =>
        euclideanRT0ComponentEval q i x •
          (∂_{basisVector i} φ) x)
      (referenceSimplex_RT0_fiberCoordinates_integrable
        q i (∂_{basisVector i} φ)))

/-- The RT0 radial interior base function is integrable. -/
theorem referenceSimplexRT0InteriorBase_integrable
    {d : Nat} (q : RT0AffineND d)
    (φ : 𝓢(EuclideanDomain d, ℂ)) (i : Fin d) :
    Integrable (referenceSimplexRT0InteriorBase q φ i) := by
  simpa [referenceSimplexRT0InteriorBase] using
    (integrable_referenceSimplex_fiberIntegral
      i
      (fun x => q.radial • φ x)
      (referenceSimplex_realConst_fiberCoordinates_integrable
        q.radial φ i))

/-- The RT0 endpoint boundary base function is integrable. -/
theorem referenceSimplexRT0BoundaryBase_integrable
    {d : Nat} (q : RT0AffineND d)
    (φ : 𝓢(EuclideanDomain d, ℂ)) (i : Fin d) :
    Integrable (referenceSimplexRT0BoundaryBase q φ i) := by
  have hD := referenceSimplexRT0DerivativeBase_integrable q φ i
  have hI := referenceSimplexRT0InteriorBase_integrable q φ i
  have heq :
      referenceSimplexRT0BoundaryBase q φ i =
        referenceSimplexRT0InteriorBase q φ i +
          referenceSimplexRT0DerivativeBase q φ i := by
    funext y
    have h := referenceSimplexRT0_base_gaussGreen q φ i y
    linear_combination h
  rw [heq]
  exact hI.add hD

/-- Explicit oriented RT0 coordinate endpoint boundary functional. -/
def referenceSimplexRT0EndpointBoundary
    {d : Nat} (q : RT0AffineND d)
    (φ : 𝓢(EuclideanDomain d, ℂ)) (i : Fin d) : ℂ :=
  ∫ y : (referenceSimplexCoordinateLine i)ᗮ,
    referenceSimplexRT0BoundaryBase q φ i y

/-- Full coordinatewise RT0 Gauss--Green identity with explicit endpoint boundary. -/
theorem referenceSimplexRT0_gaussGreen_endpoint
    {d : Nat} (q : RT0AffineND d)
    (φ : 𝓢(EuclideanDomain d, ℂ)) (i : Fin d) :
    -(∫ x,
      (euclideanReferenceSimplex d).indicator
        (fun x =>
          euclideanRT0ComponentEval q i x •
            (∂_{basisVector i} φ) x) x) =
      (∫ x,
        (euclideanReferenceSimplex d).indicator
          (fun x => q.radial • φ x) x) -
        referenceSimplexRT0EndpointBoundary q φ i := by
  have hD :=
    integral_referenceSimplex_indicator_eq_fibers
      i
      (fun x =>
        euclideanRT0ComponentEval q i x •
          (∂_{basisVector i} φ) x)
      (referenceSimplex_RT0_fiberCoordinates_integrable
        q i (∂_{basisVector i} φ))
  have hI :=
    integral_referenceSimplex_indicator_eq_fibers
      i
      (fun x => q.radial • φ x)
      (referenceSimplex_realConst_fiberCoordinates_integrable
        q.radial φ i)
  rw [hD, hI, referenceSimplexRT0EndpointBoundary]
  rw [← integral_neg]
  calc
    (∫ y : (referenceSimplexCoordinateLine i)ᗮ,
      -referenceSimplexRT0DerivativeBase q φ i y) =
        ∫ y : (referenceSimplexCoordinateLine i)ᗮ,
          (referenceSimplexRT0InteriorBase q φ i y -
            referenceSimplexRT0BoundaryBase q φ i y) := by
      apply integral_congr_ae
      filter_upwards with y
      exact referenceSimplexRT0_base_gaussGreen q φ i y
    _ =
        (∫ y : (referenceSimplexCoordinateLine i)ᗮ,
          referenceSimplexRT0InteriorBase q φ i y) -
        ∫ y : (referenceSimplexCoordinateLine i)ᗮ,
          referenceSimplexRT0BoundaryBase q φ i y := by
      rw [integral_sub
        (referenceSimplexRT0InteriorBase_integrable q φ i)
        (referenceSimplexRT0BoundaryBase_integrable q φ i)]

end

end Continuum

end CACEFormal
