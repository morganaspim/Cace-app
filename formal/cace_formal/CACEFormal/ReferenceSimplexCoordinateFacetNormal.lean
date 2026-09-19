import Mathlib
import CACEFormal.ReferenceSimplexCoordinateFacetMeasure
import CACEFormal.SimplexFacetCurrent

namespace CACEFormal

open Set
open scoped BigOperators RealInnerProductSpace

namespace Continuum

noncomputable section

/-!
# Outward normal of a reference coordinate facet

The facet opposite vertex `i.succ` is `x_i = 0`.  Its outward normal must
therefore be `-e_i`.

Rather than computing the altitude foot explicitly, the proof uses the
certified geometric normal:

* every `e_j`, `j ≠ i`, is a direction vector of the facet, so all
  nonselected normal coordinates vanish;
* Mathlib's altitude identity shows the raw outward normal has strictly
  negative `i`-component;
* the CACE normal is normalized to norm one.

These facts force the full unit normal to equal `-e_i`.
-/

/-- Zero is contained in every reference coordinate-facet affine span. -/
theorem referenceSimplex_zero_mem_coordinateFacet_affineSpan
    {d : Nat} [NeZero d] (i : Fin d) :
    (0 : EuclideanDomain d) ∈
      affineSpan ℝ
        (Set.range
          ((referenceGeometricSimplex d).faceOpposite i.succ).points) := by
  apply mem_affineSpan ℝ
  rw [Affine.Simplex.range_faceOpposite_points]
  refine ⟨0, ?_, ?_⟩
  · simp
  · simp

/-- A nonselected basis vertex belongs to the corresponding coordinate-facet affine span. -/
theorem referenceSimplex_basisVector_mem_coordinateFacet_affineSpan
    {d : Nat} [NeZero d] (i j : Fin d) (hji : j ≠ i) :
    basisVector j ∈
      affineSpan ℝ
        (Set.range
          ((referenceGeometricSimplex d).faceOpposite i.succ).points) := by
  apply mem_affineSpan ℝ
  rw [Affine.Simplex.range_faceOpposite_points]
  refine ⟨j.succ, ?_, ?_⟩
  · simpa using Fin.succ_ne_succ.mpr hji
  · simp

/-- Every nonselected basis vector is a direction vector of the coordinate facet. -/
theorem referenceSimplex_basisVector_mem_coordinateFacet_direction
    {d : Nat} [NeZero d] (i j : Fin d) (hji : j ≠ i) :
    basisVector j ∈
      (affineSpan ℝ
        (Set.range
          ((referenceGeometricSimplex d).faceOpposite i.succ).points)).direction := by
  have hj :=
    referenceSimplex_basisVector_mem_coordinateFacet_affineSpan i j hji
  have h0 :=
    referenceSimplex_zero_mem_coordinateFacet_affineSpan i
  simpa using AffineSubspace.vsub_mem_direction hj h0

/-- Every nonselected coordinate of the outward unit normal is zero. -/
theorem referenceSimplex_coordinateFacetOutwardUnitNormal_proj_ne
    {d : Nat} [NeZero d] (i j : Fin d) (hji : j ≠ i) :
    EuclideanSpace.proj j
      (simplexFacetOutwardUnitNormal
        (referenceGeometricSimplex d) i.succ) = 0 := by
  have hv :=
    referenceSimplex_basisVector_mem_coordinateFacet_direction i j hji
  have hn :=
    simplexFacetOutwardUnitNormal_mem_orthogonal
      (referenceGeometricSimplex d) i.succ
  have hinner :=
    Submodule.inner_right_of_mem_orthogonal hv hn
  simpa [basisVector, EuclideanSpace.inner_single_left] using hinner

/-- The selected coordinate of the raw coordinate-facet outward normal is strictly negative. -/
theorem referenceSimplex_coordinateFacetOutwardNormalRaw_proj_same_neg
    {d : Nat} [NeZero d] (i : Fin d) :
    EuclideanSpace.proj i
      (simplexFacetOutwardNormalRaw
        (referenceGeometricSimplex d) i.succ) < 0 := by
  let s := referenceGeometricSimplex d
  have hheight :
      ⟪s.points i.succ -ᵥ s.points 0,
        s.points i.succ -ᵥ s.altitudeFoot i.succ⟫_ℝ =
        s.height i.succ ^ 2 :=
    s.inner_vsub_vsub_altitudeFoot_eq_height_sq
      (i := i.succ) (j := 0) (Fin.succ_ne_zero i)
  have hraw :
      ⟪basisVector i,
        simplexFacetOutwardNormalRaw s i.succ⟫_ℝ =
        -(s.height i.succ ^ 2) := by
    unfold simplexFacetOutwardNormalRaw
    rw [← neg_vsub_eq_vsub_rev, inner_neg_right]
    simpa [s] using hheight
  have hproj :
      EuclideanSpace.proj i
        (simplexFacetOutwardNormalRaw s i.succ) =
          -(s.height i.succ ^ 2) := by
    simpa [basisVector, EuclideanSpace.inner_single_left] using hraw
  rw [hproj]
  exact neg_neg_of_pos (sq_pos_of_pos (Affine.Simplex.height_pos s i.succ))

/-- The selected coordinate of the normalized outward normal remains strictly negative. -/
theorem referenceSimplex_coordinateFacetOutwardUnitNormal_proj_same_neg
    {d : Nat} [NeZero d] (i : Fin d) :
    EuclideanSpace.proj i
      (simplexFacetOutwardUnitNormal
        (referenceGeometricSimplex d) i.succ) < 0 := by
  have hraw :=
    referenceSimplex_coordinateFacetOutwardNormalRaw_proj_same_neg i
  have hnorm :
      0 <
        (‖simplexFacetOutwardNormalRaw
          (referenceGeometricSimplex d) i.succ‖)⁻¹ := by
    exact inv_pos.mpr
      (norm_pos_iff.mpr
        (simplexFacetOutwardNormalRaw_ne_zero
          (referenceGeometricSimplex d) i.succ))
  simp only [simplexFacetOutwardUnitNormal, map_smul]
  exact mul_neg_of_pos_of_neg hnorm hraw

/-- The coordinate-facet outward unit normal is exactly `-e_i`. -/
theorem referenceSimplex_coordinateFacetOutwardUnitNormal_eq
    {d : Nat} [NeZero d] (i : Fin d) :
    simplexFacetOutwardUnitNormal
        (referenceGeometricSimplex d) i.succ =
      -basisVector i := by
  let n :=
    simplexFacetOutwardUnitNormal
      (referenceGeometricSimplex d) i.succ
  have hzero :
      ∀ j : Fin d, j ≠ i → EuclideanSpace.proj j n = 0 := by
    intro j hji
    exact referenceSimplex_coordinateFacetOutwardUnitNormal_proj_ne i j hji
  have hneg : EuclideanSpace.proj i n < 0 := by
    exact referenceSimplex_coordinateFacetOutwardUnitNormal_proj_same_neg i
  have hrepr :
      n = (EuclideanSpace.proj i n) • basisVector i := by
    ext j
    by_cases hji : j = i
    · subst j
      simp [basisVector]
    · have hz := hzero j hji
      simp [basisVector, hz, PiLp.single_apply, hji]
  have hnorm : ‖n‖ = 1 := by
    exact norm_simplexFacetOutwardUnitNormal
      (referenceGeometricSimplex d) i.succ
  rw [hrepr, norm_smul] at hnorm
  have hb : ‖basisVector i‖ = 1 := by
    simp [basisVector]
  rw [hb, mul_one, Real.norm_eq_abs] at hnorm
  have hi : EuclideanSpace.proj i n = -1 := by
    rcases abs_eq_one.mp hnorm with hpos | hnegone
    · exfalso
      linarith
    · exact hnegone
  rw [hrepr, hi]
  simp

/-- Selected normal component on a coordinate facet. -/
@[simp]
theorem referenceSimplex_coordinateFacetOutwardNormalComponent_same
    {d : Nat} [NeZero d] (i : Fin d) :
    simplexFacetOutwardNormalComponent
      (referenceGeometricSimplex d) i.succ i = -1 := by
  unfold simplexFacetOutwardNormalComponent
  rw [referenceSimplex_coordinateFacetOutwardUnitNormal_eq]
  simp [basisVector]

/-- Nonselected normal component on a coordinate facet. -/
@[simp]
theorem referenceSimplex_coordinateFacetOutwardNormalComponent_ne
    {d : Nat} [NeZero d] (i j : Fin d) (hji : j ≠ i) :
    simplexFacetOutwardNormalComponent
      (referenceGeometricSimplex d) i.succ j = 0 := by
  unfold simplexFacetOutwardNormalComponent
  exact referenceSimplex_coordinateFacetOutwardUnitNormal_proj_ne i j hji

end

end Continuum

end CACEFormal
