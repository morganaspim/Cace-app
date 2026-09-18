import CACEFormal.SimplexAffineL2

namespace CACEFormal

open Set
open EuclideanGeometry
open scoped RealInnerProductSpace

namespace Continuum

noncomputable section

/-!
# Geometric simplex facets and orientation

The existing CACE coordinate type `SimplexPoint d = Fin d → ℝ` carries the
sup norm.  Euclidean facet geometry therefore lives, correctly, in
`EuclideanSpace ℝ (Fin d)`, whose norm is induced by its inner product.
The canonical linear equivalence below records the algebraic coordinate bridge
back to CACE's function coordinates.

This layer fixes opposite facets, an outward normal direction, and the
signed-distance orientation.  It does not assert a simplex Gauss--Green
formula; surface-measure finiteness and integration by parts remain separate
proof obligations.
-/

/-- Euclidean ambient coordinates used for genuine orthogonal facet geometry. -/
abbrev GeometricSimplexPoint (d : Nat) :=
  EuclideanSpace ℝ (Fin d)

/-- Algebraic coordinate identification with the existing CACE simplex coordinates. -/
def euclideanSimplexPointLinearEquiv (d : Nat) :
    GeometricSimplexPoint d ≃ₗ[ℝ] SimplexPoint d :=
  WithLp.linearEquiv 2 ℝ (Fin d → ℝ)

/-- A full-dimensional affine simplex in the Euclidean ambient space. -/
abbrev GeometricSimplex (d : Nat) :=
  Affine.Simplex ℝ (GeometricSimplexPoint d) d

/-- The closed geometric cell of a bundled simplex. -/
def geometricSimplexCell {d : Nat} (s : GeometricSimplex d) :
    Set (GeometricSimplexPoint d) :=
  s.closedInterior

/-- The Euclidean simplex cell is exactly the convex hull of its vertices. -/
theorem geometricSimplexCell_eq_convexHull {d : Nat}
    (s : GeometricSimplex d) :
    geometricSimplexCell s = convexHull ℝ (Set.range s.points) := by
  simpa [geometricSimplexCell] using
    (Affine.Simplex.convexHull_eq_closedInterior s).symm

/-- The facet opposite vertex `i`. -/
def geometricSimplexFacet {d : Nat} [NeZero d]
    (s : GeometricSimplex d) (i : Fin (d + 1)) :
    Set (GeometricSimplexPoint d) :=
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
    GeometricSimplexPoint d :=
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
    GeometricSimplexPoint d →ᴬ[ℝ] ℝ :=
  s.signedInfDist i

/-- The signed distance vanishes everywhere on the opposite facet. -/
theorem simplexFacetInwardSignedDistance_eq_zero_on_facet
    {d : Nat} [NeZero d]
    (s : GeometricSimplex d) (i : Fin (d + 1))
    {x : GeometricSimplexPoint d} (hx : x ∈ geometricSimplexFacet s i) :
    simplexFacetInwardSignedDistance s i x = 0 := by
  change x ∈ (s.faceOpposite i).closedInterior at hx
  change
    (affineSpan ℝ (s.points '' {i}ᶜ)).signedInfDist (s.points i) x = 0
  apply AffineSubspace.signedInfDist_apply_of_mem
  rw [← Affine.Simplex.range_faceOpposite_points]
  exact (s.faceOpposite i).closedInterior_subset_affineSpan hx

/-- The omitted vertex lies strictly on the positive (inward) side of its facet. -/
theorem simplexFacetInwardSignedDistance_vertex_pos
    {d : Nat} [NeZero d]
    (s : GeometricSimplex d) (i : Fin (d + 1)) :
    0 < simplexFacetInwardSignedDistance s i (s.points i) := by
  change 0 < s.signedInfDist i (s.points i)
  rw [Affine.Simplex.signedInfDist_apply_self]
  exact norm_pos_iff.mpr (vsub_ne_zero.mpr (s.ne_altitudeFoot i))

end

end Continuum

end CACEFormal
