import Mathlib
import CACEFormal.ReferenceSimplexCoordinateFacetCurrent
import CACEFormal.SimplexFacetCurrent

namespace CACEFormal

open Set
open scoped BigOperators RealInnerProductSpace

namespace Continuum

noncomputable section

/-!
# Outward normal of the slanted top facet

The top facet of the reference simplex is the face opposite vertex zero.
Every successor vertex `e_j` lies in that face, so every difference
`e_j - e_k` is tangent to it.  Hence every coordinate of the outward normal
is equal.

Mathlib's altitude identity, applied at omitted vertex zero, shows each raw
normal coordinate is strictly positive.  Combining positivity with unit norm
gives the square identity

  d * n_i^2 = 1.

We deliberately retain this algebraic form instead of introducing `sqrt d`;
the later top-face Jacobian proof will show `normDet^2 = d`, so the flux
factor follows by multiplication and positivity.
-/

/-- Every basis vertex belongs to the affine span of the top facet. -/
theorem referenceSimplex_basisVector_mem_topFacet_affineSpan
    {d : Nat} [NeZero d] (j : Fin d) :
    basisVector j ∈
      affineSpan ℝ
        (Set.range
          ((referenceGeometricSimplex d).faceOpposite 0).points) := by
  apply mem_affineSpan ℝ
  rw [Affine.Simplex.range_faceOpposite_points]
  refine ⟨j.succ, ?_, ?_⟩
  · simp
  · simp

/-- Differences of basis vectors are tangent to the slanted top facet. -/
theorem referenceSimplex_basisVector_sub_mem_topFacet_direction
    {d : Nat} [NeZero d] (i j : Fin d) :
    basisVector i - basisVector j ∈
      (affineSpan ℝ
        (Set.range
          ((referenceGeometricSimplex d).faceOpposite 0).points)).direction := by
  have hi := referenceSimplex_basisVector_mem_topFacet_affineSpan i
  have hj := referenceSimplex_basisVector_mem_topFacet_affineSpan j
  simpa using AffineSubspace.vsub_mem_direction hi hj

/-- All coordinates of the top-facet outward unit normal are equal. -/
theorem referenceSimplex_topFacetOutwardUnitNormal_proj_eq
    {d : Nat} [NeZero d] (i j : Fin d) :
    EuclideanSpace.proj i
        (simplexFacetOutwardUnitNormal
          (referenceGeometricSimplex d) 0) =
      EuclideanSpace.proj j
        (simplexFacetOutwardUnitNormal
          (referenceGeometricSimplex d) 0) := by
  have hv :=
    referenceSimplex_basisVector_sub_mem_topFacet_direction i j
  have hn :=
    simplexFacetOutwardUnitNormal_mem_orthogonal
      (referenceGeometricSimplex d) 0
  have hinner :=
    Submodule.inner_right_of_mem_orthogonal hv hn
  have hzero :
      EuclideanSpace.proj i
          (simplexFacetOutwardUnitNormal
            (referenceGeometricSimplex d) 0) -
        EuclideanSpace.proj j
          (simplexFacetOutwardUnitNormal
            (referenceGeometricSimplex d) 0) = 0 := by
    simpa [basisVector, inner_sub_left,
      EuclideanSpace.inner_single_left] using hinner
  linarith

/-- Every coordinate of the raw top-facet outward normal is strictly positive. -/
theorem referenceSimplex_topFacetOutwardNormalRaw_proj_pos
    {d : Nat} [NeZero d] (i : Fin d) :
    0 <
      EuclideanSpace.proj i
        (simplexFacetOutwardNormalRaw
          (referenceGeometricSimplex d) 0) := by
  let s := referenceGeometricSimplex d
  have hheight :
      ⟪s.points 0 -ᵥ s.points i.succ,
        s.points 0 -ᵥ s.altitudeFoot 0⟫_ℝ =
        s.height 0 ^ 2 :=
    s.inner_vsub_vsub_altitudeFoot_eq_height_sq
      (i := 0) (j := i.succ) (by simp)
  have hraw :
      ⟪basisVector i,
        simplexFacetOutwardNormalRaw s 0⟫_ℝ =
        s.height 0 ^ 2 := by
    unfold simplexFacetOutwardNormalRaw
    simpa [s, inner_neg_left, inner_neg_right] using hheight
  have hproj :
      EuclideanSpace.proj i
        (simplexFacetOutwardNormalRaw s 0) =
          s.height 0 ^ 2 := by
    simpa [basisVector, EuclideanSpace.inner_single_left] using hraw
  rw [hproj]
  exact sq_pos_of_pos (Affine.Simplex.height_pos s 0)

/-- Every top-facet outward unit-normal coordinate is strictly positive. -/
theorem referenceSimplex_topFacetOutwardUnitNormal_proj_pos
    {d : Nat} [NeZero d] (i : Fin d) :
    0 <
      EuclideanSpace.proj i
        (simplexFacetOutwardUnitNormal
          (referenceGeometricSimplex d) 0) := by
  have hraw := referenceSimplex_topFacetOutwardNormalRaw_proj_pos i
  have hnorm :
      0 <
        (‖simplexFacetOutwardNormalRaw
          (referenceGeometricSimplex d) 0‖)⁻¹ := by
    exact inv_pos.mpr
      (norm_pos_iff.mpr
        (simplexFacetOutwardNormalRaw_ne_zero
          (referenceGeometricSimplex d) 0))
  simp only [simplexFacetOutwardUnitNormal, map_smul]
  exact mul_pos hnorm hraw

/--
For any coordinate of the top-facet unit normal, `d * n_i^2 = 1`.

This is the normalization identity used later to cancel the surface Jacobian
without introducing square roots.
-/
theorem referenceSimplex_topFacetOutwardUnitNormal_proj_sq
    {d : Nat} [NeZero d] (i : Fin d) :
    (d : ℝ) *
      (EuclideanSpace.proj i
        (simplexFacetOutwardUnitNormal
          (referenceGeometricSimplex d) 0)) ^ 2 = 1 := by
  let n :=
    simplexFacetOutwardUnitNormal
      (referenceGeometricSimplex d) 0
  have hnorm : ‖n‖ = 1 := by
    exact norm_simplexFacetOutwardUnitNormal
      (referenceGeometricSimplex d) 0
  have hsq : ‖n‖ ^ 2 = 1 := by
    rw [hnorm]
    norm_num
  rw [EuclideanSpace.real_norm_sq_eq] at hsq
  have hall :
      ∀ j : Fin d, n j = EuclideanSpace.proj i n := by
    intro j
    simpa using
      (referenceSimplex_topFacetOutwardUnitNormal_proj_eq
        (d := d) j i)
  have hsum :
      (∑ j : Fin d, (n j) ^ 2) =
        (d : ℝ) * (EuclideanSpace.proj i n) ^ 2 := by
    simp_rw [hall]
    simp
  rw [hsum] at hsq
  exact hsq

/-- Top-facet normal component notation agrees across coordinates. -/
theorem referenceSimplex_topFacetOutwardNormalComponent_eq
    {d : Nat} [NeZero d] (i j : Fin d) :
    simplexFacetOutwardNormalComponent
        (referenceGeometricSimplex d) 0 i =
      simplexFacetOutwardNormalComponent
        (referenceGeometricSimplex d) 0 j := by
  unfold simplexFacetOutwardNormalComponent
  exact referenceSimplex_topFacetOutwardUnitNormal_proj_eq i j

/-- Every top-facet normal component is positive. -/
theorem referenceSimplex_topFacetOutwardNormalComponent_pos
    {d : Nat} [NeZero d] (i : Fin d) :
    0 <
      simplexFacetOutwardNormalComponent
        (referenceGeometricSimplex d) 0 i := by
  unfold simplexFacetOutwardNormalComponent
  exact referenceSimplex_topFacetOutwardUnitNormal_proj_pos i

/-- Square normalization of a top-facet normal component. -/
theorem referenceSimplex_topFacetOutwardNormalComponent_sq
    {d : Nat} [NeZero d] (i : Fin d) :
    (d : ℝ) *
      (simplexFacetOutwardNormalComponent
        (referenceGeometricSimplex d) 0 i) ^ 2 = 1 := by
  unfold simplexFacetOutwardNormalComponent
  exact referenceSimplex_topFacetOutwardUnitNormal_proj_sq i

end

end Continuum

end CACEFormal
