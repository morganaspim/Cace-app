import Mathlib
import CACEFormal.ReferenceSimplexCell

namespace CACEFormal

open Set
open scoped BigOperators

namespace Continuum

noncomputable section

/-!
# Explicit facets of the geometric reference simplex

The canonical barycentric weights make the opposite facets completely
transparent:

* the facet opposite vertex zero is the slanted top face `Σ_j x_j = 1`;
* the facet opposite vertex `j.succ` is the coordinate face `x_j = 0`.

These equations are the geometric endpoint identification needed by the
fiberwise integration-by-parts proof.
-/

/--
A point lies on the facet opposite `facet` exactly when it lies in the
reference simplex and the omitted barycentric weight vanishes.
-/
theorem mem_referenceGeometricSimplex_facet_iff_weight_zero
    {d : Nat} [NeZero d]
    (facet : Fin (d + 1)) (x : EuclideanDomain d) :
    x ∈ geometricSimplexFacet (referenceGeometricSimplex d) facet ↔
      x ∈ euclideanReferenceSimplex d ∧
        referenceSimplexBarycentricWeight x facet = 0 := by
  constructor
  · intro hfacet
    have hcell :
        x ∈ euclideanReferenceSimplex d := by
      rw [← referenceGeometricSimplex_cell_eq_referenceSimplex d]
      exact geometricSimplexFacet_subset_cell
        (referenceGeometricSimplex d) facet hfacet
    refine ⟨hcell, ?_⟩
    rw [← referenceSimplex_affineCombination_barycentric x] at hfacet
    change
      Finset.univ.affineCombination ℝ
          (referenceGeometricSimplex d).points
          (referenceSimplexBarycentricWeight x) ∈
        ((referenceGeometricSimplex d).faceOpposite facet).closedInterior
      at hfacet
    unfold Affine.Simplex.faceOpposite at hfacet
    have hface :=
      (Affine.Simplex.affineCombination_mem_closedInterior_face_iff_nonneg
        (referenceGeometricSimplex d) _
        (referenceSimplexBarycentricWeight_sum x)).mp hfacet
    exact hface.2 facet (by simp)
  · rintro ⟨hx, hzero⟩
    rw [← referenceSimplex_affineCombination_barycentric x]
    change
      Finset.univ.affineCombination ℝ
          (referenceGeometricSimplex d).points
          (referenceSimplexBarycentricWeight x) ∈
        ((referenceGeometricSimplex d).faceOpposite facet).closedInterior
    unfold Affine.Simplex.faceOpposite
    apply
      (Affine.Simplex.affineCombination_mem_closedInterior_face_iff_nonneg
        (referenceGeometricSimplex d) _
        (referenceSimplexBarycentricWeight_sum x)).2
    refine ⟨?_, ?_⟩
    · intro i hi
      exact referenceSimplexBarycentricWeight_nonneg_of_mem hx i
    · intro i hi
      have hif : i = facet := by
        simpa using hi
      simpa [hif] using hzero

/-- The facet opposite vertex zero is exactly the slanted face `Σ_j x_j = 1`. -/
theorem mem_referenceGeometricSimplex_topFacet_iff
    {d : Nat} [NeZero d] (x : EuclideanDomain d) :
    x ∈ geometricSimplexFacet (referenceGeometricSimplex d) 0 ↔
      x ∈ euclideanReferenceSimplex d ∧
        (∑ j : Fin d, EuclideanSpace.proj j x) = 1 := by
  rw [mem_referenceGeometricSimplex_facet_iff_weight_zero]
  simp only [referenceSimplexBarycentricWeight_zero]
  constructor
  · rintro ⟨hx, h⟩
    exact ⟨hx, by linarith⟩
  · rintro ⟨hx, h⟩
    exact ⟨hx, by linarith⟩

/-- The facet opposite `j.succ` is exactly the coordinate face `x_j = 0`. -/
theorem mem_referenceGeometricSimplex_coordinateFacet_iff
    {d : Nat} [NeZero d] (j : Fin d) (x : EuclideanDomain d) :
    x ∈ geometricSimplexFacet (referenceGeometricSimplex d) j.succ ↔
      x ∈ euclideanReferenceSimplex d ∧
        EuclideanSpace.proj j x = 0 := by
  simpa using
    (mem_referenceGeometricSimplex_facet_iff_weight_zero
      (d := d) j.succ x)

end

end Continuum

end CACEFormal
