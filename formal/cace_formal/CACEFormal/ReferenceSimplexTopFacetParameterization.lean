import Mathlib
import CACEFormal.ReferenceSimplexTopFacetNormal

namespace CACEFormal

open Set
open scoped BigOperators RealInnerProductSpace

namespace Continuum

noncomputable section

/-!
# Linear parameterization of the reference top facet

Fix coordinate `i` and let `S = (ℝ ∙ e_i)ᗮ`.  For `y : S`, the upper
coordinate-fiber endpoint can be written

  T_i(y) = e_i + L_i(y),

where

  L_i(y) = y - (Σ_j y_j) e_i.

The translation `e_i` does not affect codimension-one Hausdorff measure, so
the later Jacobian calculation reduces entirely to the linear map `L_i`.
-/

/-- Total coordinate-sum functional on the orthogonal base hyperplane. -/
noncomputable def referenceSimplexCoordinateSumLinearMap
    {d : Nat} (i : Fin d) :
    (referenceSimplexCoordinateLine i)ᗮ →ₗ[ℝ] ℝ :=
  ∑ j : Fin d,
    (EuclideanSpace.projₗ j).comp
      (referenceSimplexCoordinateLine i)ᗮ.subtype

@[simp]
theorem referenceSimplexCoordinateSumLinearMap_apply
    {d : Nat} (i : Fin d)
    (y : (referenceSimplexCoordinateLine i)ᗮ) :
    referenceSimplexCoordinateSumLinearMap i y =
      ∑ j : Fin d, EuclideanSpace.proj j (y : EuclideanDomain d) := by
  simp [referenceSimplexCoordinateSumLinearMap]

/--
Linear part of the upper-endpoint graph parameterization.

The selected coordinate receives the negative total coordinate sum, while all
orthogonal-base coordinates are retained.
-/
noncomputable def referenceSimplexTopLinearMap
    {d : Nat} (i : Fin d) :
    (referenceSimplexCoordinateLine i)ᗮ →ₗ[ℝ] EuclideanDomain d :=
  (referenceSimplexCoordinateLine i)ᗮ.subtype -
    LinearMap.smulRight
      (referenceSimplexCoordinateSumLinearMap i)
      (basisVector i)

@[simp]
theorem referenceSimplexTopLinearMap_apply
    {d : Nat} (i : Fin d)
    (y : (referenceSimplexCoordinateLine i)ᗮ) :
    referenceSimplexTopLinearMap i y =
      (y : EuclideanDomain d) -
        (∑ j : Fin d, EuclideanSpace.proj j (y : EuclideanDomain d)) •
          basisVector i := by
  simp [referenceSimplexTopLinearMap,
    referenceSimplexCoordinateSumLinearMap]

/-- The upper endpoint of the coordinate fiber, as a function of the orthogonal base point. -/
noncomputable def referenceSimplexTopEndpoint
    {d : Nat} (i : Fin d)
    (y : (referenceSimplexCoordinateLine i)ᗮ) :
    EuclideanDomain d :=
  referenceSimplexFiberPoint i (y : EuclideanDomain d)
    (referenceSimplexFiberUpper i (y : EuclideanDomain d))

/-- On the orthogonal base hyperplane, the nonselected coordinate sum is the full coordinate sum. -/
theorem referenceSimplexOtherCoordinateSum_eq_coordinateSum_on_base
    {d : Nat} (i : Fin d)
    (y : (referenceSimplexCoordinateLine i)ᗮ) :
    referenceSimplexOtherCoordinateSum i (y : EuclideanDomain d) =
      ∑ j : Fin d, EuclideanSpace.proj j (y : EuclideanDomain d) := by
  have hsplit :=
    referenceSimplex_coordinate_sum_split i (y : EuclideanDomain d)
  have hi := referenceSimplexBase_proj_eq_zero i y
  rw [hi, add_zero] at hsplit
  exact hsplit

/-- Exact affine decomposition of the top endpoint: `T_i(y) = e_i + L_i(y)`. -/
theorem referenceSimplexTopEndpoint_eq
    {d : Nat} (i : Fin d)
    (y : (referenceSimplexCoordinateLine i)ᗮ) :
    referenceSimplexTopEndpoint i y =
      basisVector i + referenceSimplexTopLinearMap i y := by
  have hi := referenceSimplexBase_proj_eq_zero i y
  have hsum :=
    referenceSimplexOtherCoordinateSum_eq_coordinateSum_on_base i y
  simp only [referenceSimplexTopEndpoint, referenceSimplexFiberPoint,
    referenceSimplexFiberUpper, referenceSimplexTopLinearMap_apply, hi,
    sub_zero]
  rw [hsum, sub_smul, one_smul]
  abel

/-- Every admissible top endpoint lies on the geometric top facet. -/
theorem referenceSimplexTopEndpoint_mem_topFacet
    {d : Nat} [NeZero d] (i : Fin d)
    (y : (referenceSimplexCoordinateLine i)ᗮ)
    (hy : y ∈ referenceSimplexFiberBaseDomain i) :
    referenceSimplexTopEndpoint i y ∈
      geometricSimplexFacet (referenceGeometricSimplex d) 0 := by
  exact referenceSimplex_upperEndpoint_mem_topFacet i y hy

/-- Nonselected coordinates are preserved by the top endpoint parameterization. -/
theorem referenceSimplexTopEndpoint_proj_ne
    {d : Nat} (i j : Fin d) (hji : j ≠ i)
    (y : (referenceSimplexCoordinateLine i)ᗮ) :
    EuclideanSpace.proj j (referenceSimplexTopEndpoint i y) =
      EuclideanSpace.proj j (y : EuclideanDomain d) := by
  exact referenceSimplexFiberPoint_proj_ne
    i j (y : EuclideanDomain d)
    (referenceSimplexFiberUpper i (y : EuclideanDomain d)) hji

/-- The selected top-endpoint coordinate is the fiber upper endpoint. -/
@[simp]
theorem referenceSimplexTopEndpoint_proj_same
    {d : Nat} (i : Fin d)
    (y : (referenceSimplexCoordinateLine i)ᗮ) :
    EuclideanSpace.proj i (referenceSimplexTopEndpoint i y) =
      referenceSimplexFiberUpper i (y : EuclideanDomain d) := by
  exact referenceSimplexFiberPoint_proj_same
    i (y : EuclideanDomain d)
    (referenceSimplexFiberUpper i (y : EuclideanDomain d))

end

end Continuum

end CACEFormal
