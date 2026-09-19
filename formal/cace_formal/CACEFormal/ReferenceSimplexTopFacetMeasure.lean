import Mathlib
import CACEFormal.ReferenceSimplexTopFacetFluxFactor
import CACEFormal.SimplexFacetMeasure

namespace CACEFormal

open Set MeasureTheory
open EuclideanGeometry
open scoped BigOperators MeasureTheory RealInnerProductSpace

namespace Continuum

noncomputable section

/-!
# Surface measure of the reference top facet

The top endpoint map is the translation by `e_i` of the injective linear map
`L_i`.  Translation preserves normalized Euclidean Hausdorff measure, while
Mathlib's `LinearMap.euclideanHausdorffMeasure_image_eq_normDet_mul_volume`
scales the linear image by `normDet(L_i)`.

Thus for every set `A` in the orthogonal base hyperplane,

  μHE[d-1] (T_i '' A) = ofReal(normDet L_i) * volume A.

The admissible base domain maps exactly onto the top facet.  Restricting the
image-scaling identity therefore gives the precise top-facet surface measure.
-/

/-- The top linear map is injective. -/
theorem referenceSimplexTopLinearMap_injective
    {d : Nat} [NeZero d] (i : Fin d) :
    Function.Injective (referenceSimplexTopLinearMap i) := by
  apply LinearMap.ker_eq_bot.mp
  by_contra hker
  have hzero :
      (referenceSimplexTopLinearMap i).normDet = 0 :=
    (LinearMap.normDet_eq_zero_iff_ker_ne_bot).2 hker
  exact (ne_of_gt (referenceSimplexTopLinearMap_normDet_pos i)) hzero

/-- The top endpoint parameterization is injective. -/
theorem referenceSimplexTopEndpoint_injective
    {d : Nat} [NeZero d] (i : Fin d) :
    Function.Injective (referenceSimplexTopEndpoint i) := by
  intro x y hxy
  apply referenceSimplexTopLinearMap_injective i
  have hx := referenceSimplexTopEndpoint_eq i x
  have hy := referenceSimplexTopEndpoint_eq i y
  rw [hx, hy] at hxy
  exact add_left_cancel hxy

/-- The top endpoint parameterization is continuous, hence measurable. -/
theorem referenceSimplexTopEndpoint_continuous
    {d : Nat} (i : Fin d) :
    Continuous (referenceSimplexTopEndpoint i) := by
  have hL :
      Continuous (referenceSimplexTopLinearMap i) :=
    LinearMap.continuous_of_finiteDimensional
      (referenceSimplexTopLinearMap i)
  have h :
      Continuous
        (fun y : (referenceSimplexCoordinateLine i)ᗮ =>
          basisVector i + referenceSimplexTopLinearMap i y) :=
    continuous_const.add hL
  apply h.congr
  intro y
  exact (referenceSimplexTopEndpoint_eq i y).symm

/--
The top endpoint map scales codimension-one Euclidean Hausdorff measure by the
norm determinant of its linear part.
-/
theorem referenceSimplexTopEndpoint_euclideanHausdorffMeasure_image
    {d : Nat} [NeZero d] (i : Fin d)
    (A : Set ((referenceSimplexCoordinateLine i)ᗮ)) :
    (μHE[d - 1] : Measure (EuclideanDomain d))
        (referenceSimplexTopEndpoint i '' A) =
      ENNReal.ofReal ((referenceSimplexTopLinearMap i).normDet) *
        volume A := by
  let L := referenceSimplexTopLinearMap i
  let τ : EuclideanDomain d ≃ᵢ EuclideanDomain d :=
    IsometryEquiv.vaddConst (basisVector i)
  have himage :
      referenceSimplexTopEndpoint i '' A =
        τ '' (L '' A) := by
    ext x
    constructor
    · rintro ⟨y, hy, rfl⟩
      refine ⟨L y, ⟨y, hy, rfl⟩, ?_⟩
      simp [τ, referenceSimplexTopEndpoint_eq, add_comm]
    · rintro ⟨z, ⟨y, hy, rfl⟩, rfl⟩
      refine ⟨y, hy, ?_⟩
      simp [τ, referenceSimplexTopEndpoint_eq, add_comm]
  rw [himage]
  rw [τ.isometry.euclideanHausdorffMeasure_image]
  have hfin :
      Module.finrank ℝ ((referenceSimplexCoordinateLine i)ᗮ) = d - 1 :=
    referenceSimplexCoordinateLine_orthogonal_finrank i
  simpa [L, hfin] using
    (LinearMap.euclideanHausdorffMeasure_image_eq_normDet_mul_volume
      (referenceSimplexTopLinearMap i) A)

/-- The admissible base domain maps onto the entire geometric top facet. -/
theorem referenceSimplexTopEndpoint_image_baseDomain
    {d : Nat} [NeZero d] (i : Fin d) :
    referenceSimplexTopEndpoint i ''
        referenceSimplexFiberBaseDomain i =
      geometricSimplexFacet (referenceGeometricSimplex d) 0 := by
  ext x
  constructor
  · rintro ⟨y, hy, rfl⟩
    exact referenceSimplexTopEndpoint_mem_topFacet i y hy
  · intro hx
    have htop :=
      (mem_referenceGeometricSimplex_topFacet_iff x).mp hx
    let t : ℝ := EuclideanSpace.proj i x
    let y0 : EuclideanDomain d := x - t • basisVector i
    have hyorth :
        y0 ∈ (referenceSimplexCoordinateLine i)ᗮ := by
      apply
        (mem_referenceSimplexCoordinateLine_orthogonal_iff i y0).2
      simp [y0, t, basisVector]
    let y : (referenceSimplexCoordinateLine i)ᗮ := ⟨y0, hyorth⟩
    have hyi :
        EuclideanSpace.proj i (y : EuclideanDomain d) = 0 :=
      referenceSimplexBase_proj_eq_zero i y
    have hfiber :
        referenceSimplexFiberPoint i (y : EuclideanDomain d) t = x := by
      simp [referenceSimplexFiberPoint, y, y0, t, hyi]
    have hmem :
        referenceSimplexFiberPoint i (y : EuclideanDomain d) t ∈
          euclideanReferenceSimplex d := by
      rw [hfiber]
      exact htop.1
    have hybase :
        y ∈ referenceSimplexFiberBaseDomain i :=
      ((referenceSimplexFiberPoint_mem_iff_baseDomain i y t).mp hmem).1
    have hsumfiber :
        (∑ j : Fin d,
          EuclideanSpace.proj j
            (referenceSimplexFiberPoint i
              (y : EuclideanDomain d) t)) = 1 := by
      rw [hfiber]
      exact htop.2
    have hupper :
        referenceSimplexFiberUpper i (y : EuclideanDomain d) = t := by
      have hsplit :=
        referenceSimplex_coordinate_sum_split i
          (referenceSimplexFiberPoint i (y : EuclideanDomain d) t)
      rw [referenceSimplexOtherCoordinateSum_fiberPoint,
        referenceSimplexFiberPoint_proj_same, hsumfiber] at hsplit
      unfold referenceSimplexFiberUpper
      linarith
    refine ⟨y, hybase, ?_⟩
    unfold referenceSimplexTopEndpoint
    rw [hupper, hfiber]

/--
Scaled pushforward of restricted base volume is exactly the top-facet surface
measure.
-/
theorem referenceSimplex_topFacetSurfaceMeasure_eq_scaled_map
    {d : Nat} [NeZero d] (i : Fin d) :
    ENNReal.ofReal ((referenceSimplexTopLinearMap i).normDet) •
      ((volume.restrict (referenceSimplexFiberBaseDomain i)).map
        (referenceSimplexTopEndpoint i)) =
      geometricSimplexFacetSurfaceMeasure
        (referenceGeometricSimplex d) 0 := by
  apply Measure.ext
  intro A hA
  have hTmeas : Measurable (referenceSimplexTopEndpoint i) :=
    (referenceSimplexTopEndpoint_continuous i).measurable
  have hpre : MeasurableSet
      ((referenceSimplexTopEndpoint i) ⁻¹' A) :=
    hA.preimage hTmeas
  rw [Measure.smul_apply]
  rw [Measure.map_apply hTmeas hA]
  rw [Measure.restrict_apply hpre]
  rw [geometricSimplexFacetSurfaceMeasure, Measure.restrict_apply hA]
  have hset :
      A ∩ geometricSimplexFacet (referenceGeometricSimplex d) 0 =
        referenceSimplexTopEndpoint i ''
          (((referenceSimplexTopEndpoint i) ⁻¹' A) ∩
            referenceSimplexFiberBaseDomain i) := by
    rw [← referenceSimplexTopEndpoint_image_baseDomain i]
    ext x
    constructor
    · rintro ⟨hxA, y, hybase, rfl⟩
      exact ⟨y, ⟨hxA, hybase⟩, rfl⟩
    · rintro ⟨y, ⟨hyA, hybase⟩, rfl⟩
      exact ⟨hyA, ⟨y, hybase, rfl⟩⟩
  rw [hset]
  exact
    referenceSimplexTopEndpoint_euclideanHausdorffMeasure_image
      i
      (((referenceSimplexTopEndpoint i) ⁻¹' A) ∩
        referenceSimplexFiberBaseDomain i)

end

end Continuum

end CACEFormal
