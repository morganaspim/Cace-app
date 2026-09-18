import CACEFormal.SimplexAffineL2

namespace CACEFormal

open Set
open EuclideanGeometry
open scoped RealInnerProductSpace

namespace Continuum

noncomputable section

/-!
# Geometric simplex facets and orientation

This layer connects the measure-theoretic simplex support used by CACE to
Mathlib's bundled affine simplex geometry.  It fixes the opposite-facet sets,
the outward normal direction, and the signed-distance orientation without
asserting a simplex Gauss--Green theorem.

The later boundary-current layer may use these certified geometric objects;
surface-measure finiteness and integration by parts remain separate proof
obligations.
-/

/-- A full-dimensional affine simplex in the CACE Euclidean ambient space. -/
abbrev GeometricSimplex (d : Nat) :=
  Affine.Simplex ℝ (SimplexPoint d) d

/-- The closed geometric cell of a bundled simplex. -/
def geometricSimplexCell {d : Nat} (s : GeometricSimplex d) :
    Set (SimplexPoint d) :=
  s.closedInterior

/-- The earlier convex-hull support is exactly Mathlib's closed simplex interior. -/
theorem simplexSet_points_eq_geometricSimplexCell {d : Nat}
    (s : GeometricSimplex d) :
    simplexSet s.points = geometricSimplexCell s := by
  simpa [simplexSet, geometricSimplexCell] using
    (Affine.Simplex.convexHull_eq_closedInterior s)

/-- The facet opposite vertex `i`. -/
def geometricSimplexFacet {d : Nat} [NeZero d]
    (s : GeometricSimplex d) (i : Fin (d + 1)) :
    Set (SimplexPoint d) :=
  (s.faceOpposite i).closedInterior

/-- Every opposite facet lies in the closed simplex cell. -/
theorem geometricSimplexFacet_subset_cell {d : Nat} [NeZero d]
    (s : GeometricSimplex d) (i : Fin (d + 1)) :
    geometricSimplexFacet s i ⊆ geometricSimplexCell s := by
  exact s.closedInterior_faceOpposite_subset_closedInterior i

/-- Opposite facets are compact. -/
theorem geometricSimplexFacet_compact {d : Nat} [NeZero d]
    (s : GeometricSimplex d) (i : Fin (d + 1)) :
    IsCompact (geometricSimplexFacet s i) := by
  exact (s.faceOpposite i).isCompact_closedInterior

/-- Opposite facets are measurable. -/
theorem geometricSimplexFacet_measurable {d : Nat} [NeZero d]
    (s : GeometricSimplex d) (i : Fin (d + 1)) :
    MeasurableSet (geometricSimplexFacet s i) :=
  (geometricSimplexFacet_compact s i).isClosed.measurableSet

/--
Raw outward normal direction: from the omitted vertex toward its orthogonal
projection on the opposite facet.  Normalization is intentionally deferred.
-/
noncomputable def simplexFacetOutwardNormalRaw {d : Nat} [NeZero d]
    (s : GeometricSimplex d) (i : Fin (d + 1)) :
    SimplexPoint d :=
  s.altitudeFoot i -ᵥ s.points i

/-- Nondegeneracy of the simplex makes every raw facet normal nonzero. -/
theorem simplexFacetOutwardNormalRaw_ne_zero {d : Nat} [NeZero d]
    (s : GeometricSimplex d) (i : Fin (d + 1)) :
    simplexFacetOutwardNormalRaw s i ≠ 0 := by
  exact vsub_ne_zero.mpr (s.ne_altitudeFoot i).symm

/-- The raw outward normal is orthogonal to the affine direction of its facet. -/
theorem simplexFacetOutwardNormalRaw_mem_orthogonal {d : Nat} [NeZero d]
    (s : GeometricSimplex d) (i : Fin (d + 1)) :
    simplexFacetOutwardNormalRaw s i ∈
      (affineSpan ℝ (Set.range (s.faceOpposite i).points)).directionᗮ := by
  rw [simplexFacetOutwardNormalRaw, Affine.Simplex.altitudeFoot,
    Affine.Simplex.orthogonalProjectionSpan]
  exact orthogonalProjection_vsub_mem_direction_orthogonal _ _

/--
Signed distance to the opposite facet, positive in the direction of the omitted
vertex.  Thus its negative direction is the outward orientation chosen above.
-/
noncomputable def simplexFacetInwardSignedDistance {d : Nat} [NeZero d]
    (s : GeometricSimplex d) (i : Fin (d + 1)) :
    SimplexPoint d →ᴬ[ℝ] ℝ :=
  s.signedInfDist i

/-- The signed distance vanishes everywhere on the opposite facet. -/
theorem simplexFacetInwardSignedDistance_eq_zero_on_facet
    {d : Nat} [NeZero d]
    (s : GeometricSimplex d) (i : Fin (d + 1))
    {x : SimplexPoint d} (hx : x ∈ geometricSimplexFacet s i) :
    simplexFacetInwardSignedDistance s i x = 0 := by
  change x ∈ (s.faceOpposite i).closedInterior at hx
  rw [simplexFacetInwardSignedDistance, Affine.Simplex.signedInfDist]
  apply AffineSubspace.signedInfDist_apply_of_mem
  rw [← Affine.Simplex.range_faceOpposite_points]
  exact (s.faceOpposite i).closedInterior_subset_affineSpan hx

/-- The omitted vertex lies strictly on the positive (inward) side of its facet. -/
theorem simplexFacetInwardSignedDistance_vertex_pos
    {d : Nat} [NeZero d]
    (s : GeometricSimplex d) (i : Fin (d + 1)) :
    0 < simplexFacetInwardSignedDistance s i (s.points i) := by
  rw [simplexFacetInwardSignedDistance, Affine.Simplex.signedInfDist_apply_self]
  exact norm_pos_iff.mpr (vsub_ne_zero.mpr (s.ne_altitudeFoot i))

end

end Continuum

end CACEFormal
