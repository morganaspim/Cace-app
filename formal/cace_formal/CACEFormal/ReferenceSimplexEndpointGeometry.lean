import Mathlib
import CACEFormal.ReferenceSimplexFacets
import CACEFormal.ReferenceSimplexFiberDomain

namespace CACEFormal

open Set
open scoped BigOperators

namespace Continuum

noncomputable section

/-!
# Geometric location of reference-simplex fiber endpoints

For an admissible orthogonal base point:

* the lower endpoint `t = 0` lies on the coordinate facet opposite
  `i.succ`;
* the upper endpoint `t = referenceSimplexFiberUpper i y` lies on the top
  facet opposite vertex zero.

This is the set-theoretic endpoint-to-facet bridge needed before comparing
fiber endpoint measures with the geometric facet surface measures.
-/

/-- An orthogonal base point has zero selected coordinate. -/
theorem referenceSimplexBase_proj_eq_zero
    {d : Nat} (i : Fin d)
    (y : (referenceSimplexCoordinateLine i)ᗮ) :
    EuclideanSpace.proj i (y : EuclideanDomain d) = 0 :=
  (mem_referenceSimplexCoordinateLine_orthogonal_iff
    i (y : EuclideanDomain d)).mp y.property

/-- On the orthogonal base hyperplane, the lower fiber endpoint is literally the base point. -/
theorem referenceSimplexFiberPoint_zero_eq_base
    {d : Nat} (i : Fin d)
    (y : (referenceSimplexCoordinateLine i)ᗮ) :
    referenceSimplexFiberPoint i (y : EuclideanDomain d) 0 =
      (y : EuclideanDomain d) := by
  rw [← referenceSimplexFiberPoint_original i (y : EuclideanDomain d)]
  rw [referenceSimplexBase_proj_eq_zero i y]

/-- The lower endpoint of an admissible fiber lies on coordinate facet `i`. -/
theorem referenceSimplex_lowerEndpoint_mem_coordinateFacet
    {d : Nat} [NeZero d] (i : Fin d)
    (y : (referenceSimplexCoordinateLine i)ᗮ)
    (hy : y ∈ referenceSimplexFiberBaseDomain i) :
    referenceSimplexFiberPoint i (y : EuclideanDomain d) 0 ∈
      geometricSimplexFacet (referenceGeometricSimplex d) i.succ := by
  apply
    (mem_referenceGeometricSimplex_coordinateFacet_iff
      i (referenceSimplexFiberPoint i (y : EuclideanDomain d) 0)).2
  refine ⟨?_, ?_⟩
  · exact referenceSimplexFiberPoint_zero_mem
      i (y : EuclideanDomain d) hy.1
      (referenceSimplexFiberUpper_nonneg_of_baseDomain i hy)
  · simp

/-- At the upper endpoint, the full coordinate sum is exactly one. -/
theorem referenceSimplex_upperEndpoint_coordinateSum
    {d : Nat} (i : Fin d)
    (y : (referenceSimplexCoordinateLine i)ᗮ) :
    (∑ j : Fin d,
      EuclideanSpace.proj j
        (referenceSimplexFiberPoint i (y : EuclideanDomain d)
          (referenceSimplexFiberUpper i (y : EuclideanDomain d)))) = 1 := by
  rw [← referenceSimplex_coordinate_sum_split i]
  rw [referenceSimplexOtherCoordinateSum_fiberPoint,
    referenceSimplexFiberPoint_proj_same]
  unfold referenceSimplexFiberUpper
  ring

/-- The upper endpoint of an admissible fiber lies on the slanted top facet. -/
theorem referenceSimplex_upperEndpoint_mem_topFacet
    {d : Nat} [NeZero d] (i : Fin d)
    (y : (referenceSimplexCoordinateLine i)ᗮ)
    (hy : y ∈ referenceSimplexFiberBaseDomain i) :
    referenceSimplexFiberPoint i (y : EuclideanDomain d)
        (referenceSimplexFiberUpper i (y : EuclideanDomain d)) ∈
      geometricSimplexFacet (referenceGeometricSimplex d) 0 := by
  apply
    (mem_referenceGeometricSimplex_topFacet_iff
      (referenceSimplexFiberPoint i (y : EuclideanDomain d)
        (referenceSimplexFiberUpper i (y : EuclideanDomain d)))).2
  refine ⟨?_, referenceSimplex_upperEndpoint_coordinateSum i y⟩
  exact referenceSimplexFiberPoint_upper_mem
    i (y : EuclideanDomain d) hy.1
    (referenceSimplexFiberUpper_nonneg_of_baseDomain i hy)

end

end Continuum

end CACEFormal
