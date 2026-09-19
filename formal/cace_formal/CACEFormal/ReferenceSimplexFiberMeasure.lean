import Mathlib
import CACEFormal.ReferenceSimplexFiberDecomposition

namespace CACEFormal

open Set MeasureTheory
open scoped BigOperators MeasureTheory

namespace Continuum

noncomputable section

/-!
# Measure decomposition along reference-simplex coordinate fibers

This module connects the concrete fiber geometry with Mathlib's canonical
orthogonal decomposition of Euclidean volume.

For a fixed coordinate `i`:
* `referenceSimplexCoordinateLine i = ℝ ∙ e_i`;
* its orthogonal complement is the zero-`i` coordinate hyperplane;
* `LinearIsometryEquiv.toSpanUnitSingleton` identifies the line with `ℝ`
  without a Jacobian factor because `‖e_i‖ = 1`;
* `Submodule.measurePreserving_measurableEquivProd` decomposes ambient
  Euclidean volume as product volume on the line and its orthogonal complement.

The final theorem is a generic Fubini identity for any integrable transformed
integrand.  The simplex-specific indicator reduction is proved in the next layer.
-/

/-- Canonical coordinate basis vectors have unit norm. -/
@[simp]
theorem basisVector_norm {d : Nat} (i : Fin d) :
    ‖basisVector i‖ = 1 := by
  simp [basisVector]

/-- Isometric identification of the scalar line with the coordinate line. -/
noncomputable def referenceSimplexCoordinateLineEquiv {d : Nat}
    (i : Fin d) :
    ℝ ≃ₗᵢ[ℝ] referenceSimplexCoordinateLine i :=
  LinearIsometryEquiv.toSpanUnitSingleton
    (basisVector i) (basisVector_norm i)

/-- The line equivalence is concretely scalar multiplication by `e_i`. -/
@[simp]
theorem referenceSimplexCoordinateLineEquiv_apply_coe
    {d : Nat} (i : Fin d) (t : ℝ) :
    ((referenceSimplexCoordinateLineEquiv i t :
      referenceSimplexCoordinateLine i) : EuclideanDomain d) =
      t • basisVector i := by
  simp [referenceSimplexCoordinateLineEquiv]

/--
Adding a coordinate-line point to an orthogonal base point is exactly the
concrete fiber parameterization.
-/
theorem coordinateLine_add_orthogonal_eq_fiberPoint
    {d : Nat} (i : Fin d)
    (y : (referenceSimplexCoordinateLine i)ᗮ) (t : ℝ) :
    ((referenceSimplexCoordinateLineEquiv i t :
        referenceSimplexCoordinateLine i) : EuclideanDomain d) +
        (y : EuclideanDomain d) =
      referenceSimplexFiberPoint i (y : EuclideanDomain d) t := by
  have hyi : EuclideanSpace.proj i (y : EuclideanDomain d) = 0 :=
    (mem_referenceSimplexCoordinateLine_orthogonal_iff
      i (y : EuclideanDomain d)).mp y.property
  simp [referenceSimplexFiberPoint, hyi, add_comm]

/--
The inverse of Mathlib's orthogonal measurable equivalence agrees with the
concrete CACE fiber coordinates after identifying the line factor with `ℝ`.
-/
theorem measurableEquivProd_symm_coordinateFiber
    {d : Nat} (i : Fin d)
    (y : (referenceSimplexCoordinateLine i)ᗮ) (t : ℝ) :
    ((referenceSimplexCoordinateLine i).measurableEquivProd
        (0 : EuclideanDomain d)).symm
      (referenceSimplexCoordinateLineEquiv i t, y) =
      referenceSimplexFiberPoint i (y : EuclideanDomain d) t := by
  rw [Submodule.measurableEquivProd_symm_apply]
  simp [coordinateLine_add_orthogonal_eq_fiberPoint]

/--
Ambient Euclidean integration is exactly integration over the coordinate line
times its orthogonal hyperplane.
-/
theorem integral_eq_coordinateLine_prod
    {d : Nat} {F : Type*}
    [NormedAddCommGroup F] [NormedSpace ℝ F]
    (i : Fin d) (f : EuclideanDomain d → F) :
    (∫ x, f x) =
      ∫ q :
        referenceSimplexCoordinateLine i ×
          (referenceSimplexCoordinateLine i)ᗮ,
        f ((q.1 : EuclideanDomain d) + (q.2 : EuclideanDomain d)) := by
  let s := referenceSimplexCoordinateLine i
  let e := s.measurableEquivProd (0 : EuclideanDomain d)
  have h :=
    (s.measurePreserving_measurableEquivProd (0 : EuclideanDomain d))
      .integral_comp'
        (fun q : s × sᗮ => f (e.symm q))
  rw [InnerProductSpace.euclideanHausdorffMeasure_eq_volume] at h
  simpa [s, e, Submodule.measurableEquivProd_symm_apply] using h

/--
Integrability is preserved when ambient Euclidean coordinates are replaced by
the canonical coordinate-line/orthogonal-hyperplane product coordinates.
-/
theorem Integrable.coordinateLine_prod
    {d : Nat} {F : Type*}
    [NormedAddCommGroup F] [NormedSpace ℝ F]
    (i : Fin d) {f : EuclideanDomain d → F}
    (hf : Integrable f) :
    Integrable
      (fun q :
        referenceSimplexCoordinateLine i ×
          (referenceSimplexCoordinateLine i)ᗮ =>
        f ((q.1 : EuclideanDomain d) + (q.2 : EuclideanDomain d))) := by
  let s := referenceSimplexCoordinateLine i
  let e := s.measurableEquivProd (0 : EuclideanDomain d)
  have hmp :=
    (s.measurePreserving_measurableEquivProd (0 : EuclideanDomain d)).symm
  rw [InnerProductSpace.euclideanHausdorffMeasure_eq_volume] at hmp
  have hcomp : Integrable (f ∘ e.symm) :=
    hmp.integrable_comp_of_integrable hf
  simpa [s, e, Function.comp_def,
    Submodule.measurableEquivProd_symm_apply] using hcomp

/-- Integration over the coordinate line is ordinary Lebesgue integration in its scalar parameter. -/
theorem integral_coordinateLine_eq_real
    {d : Nat} {F : Type*}
    [NormedAddCommGroup F] [NormedSpace ℝ F]
    (i : Fin d) (g : referenceSimplexCoordinateLine i → F) :
    (∫ z, g z) =
      ∫ t : ℝ, g (referenceSimplexCoordinateLineEquiv i t) := by
  have hmp :
      MeasurePreserving
        (referenceSimplexCoordinateLineEquiv i)
        (volume : Measure ℝ)
        (volume : Measure (referenceSimplexCoordinateLine i)) :=
    (referenceSimplexCoordinateLineEquiv i).measurePreserving
  have h :=
    hmp.integral_comp
      (referenceSimplexCoordinateLineEquiv i).toHomeomorph.measurableEmbedding
      g
  exact h.symm

/--
Generic Fubini identity in concrete CACE fiber coordinates.

The sole hypothesis is integrability after the orthogonal product
decomposition.  Later simplex-supported integrands satisfy it because their
support is compact and their factors are continuous.
-/
theorem integral_eq_orthogonalFiber_integral
    {d : Nat} {F : Type*}
    [NormedAddCommGroup F] [NormedSpace ℝ F]
    (i : Fin d) (f : EuclideanDomain d → F)
    (hf :
      Integrable
        (fun q :
          referenceSimplexCoordinateLine i ×
            (referenceSimplexCoordinateLine i)ᗮ =>
          f ((q.1 : EuclideanDomain d) + (q.2 : EuclideanDomain d)))) :
    (∫ x, f x) =
      ∫ y : (referenceSimplexCoordinateLine i)ᗮ,
        ∫ t : ℝ,
          f (referenceSimplexFiberPoint i (y : EuclideanDomain d) t) := by
  calc
    (∫ x, f x) =
        ∫ q :
          referenceSimplexCoordinateLine i ×
            (referenceSimplexCoordinateLine i)ᗮ,
          f ((q.1 : EuclideanDomain d) + (q.2 : EuclideanDomain d)) :=
      integral_eq_coordinateLine_prod i f
    _ =
        ∫ y : (referenceSimplexCoordinateLine i)ᗮ,
          ∫ z : referenceSimplexCoordinateLine i,
            f ((z : EuclideanDomain d) + (y : EuclideanDomain d)) :=
      MeasureTheory.integral_prod_symm _ hf
    _ =
        ∫ y : (referenceSimplexCoordinateLine i)ᗮ,
          ∫ t : ℝ,
            f (referenceSimplexFiberPoint i (y : EuclideanDomain d) t) := by
      apply integral_congr_ae
      filter_upwards with y
      rw [integral_coordinateLine_eq_real]
      apply integral_congr_ae
      filter_upwards with t
      rw [coordinateLine_add_orthogonal_eq_fiberPoint]

end

end Continuum

end CACEFormal
