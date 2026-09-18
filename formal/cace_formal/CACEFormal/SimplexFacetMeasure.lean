import CACEFormal.SimplexFacetGeometry

namespace CACEFormal

open Set MeasureTheory
open EuclideanGeometry
open scoped MeasureTheory RealInnerProductSpace

namespace Continuum

noncomputable section

/-!
# Simplex facet surface measure

This layer constructs the genuine codimension-one Euclidean Hausdorff measure
on an opposite simplex facet and proves that its restriction to the compact
facet is finite.

The proof is intrinsic: the facet is first regarded inside its own affine span,
whose translation space has dimension `d - 1`.  Finite measure there is
transported through the affine-subspace isometric inclusion.  We do not use the
false generic shortcut that compactness alone would make ambient
lower-dimensional Hausdorff measure finite.

No Gauss--Green or integration-by-parts theorem is asserted here.
-/

/-- The intrinsic closed facet maps exactly onto the ambient opposite facet. -/
theorem geometricSimplexFacetInSpan_image {d : Nat} [NeZero d]
    (s : GeometricSimplex d) (i : Fin (d + 1)) :
    ((Subtype.val : geometricSimplexFacetSpan s i → GeometricSimplexPoint d) ''
        (geometricSimplexFacetInSpan s i).closedInterior) =
      geometricSimplexFacet s i := by
  ext x
  constructor
  · rintro ⟨y, hy, rfl⟩
    change (y : GeometricSimplexPoint d) ∈ (s.faceOpposite i).closedInterior
    change y ∈
      ((s.faceOpposite i).restrict (geometricSimplexFacetSpan s i) le_rfl).closedInterior at hy
    rw [Affine.Simplex.closedInterior_restrict] at hy
    exact hy
  · intro hx
    change x ∈ (s.faceOpposite i).closedInterior at hx
    have hspan : x ∈ geometricSimplexFacetSpan s i := by
      simpa [geometricSimplexFacetSpan] using
        (s.faceOpposite i).closedInterior_subset_affineSpan hx
    let y : geometricSimplexFacetSpan s i := ⟨x, hspan⟩
    refine ⟨y, ?_, rfl⟩
    change y ∈
      ((s.faceOpposite i).restrict (geometricSimplexFacetSpan s i) le_rfl).closedInterior
    rw [Affine.Simplex.closedInterior_restrict]
    exact hx

/--
The intrinsic facet has finite `(d - 1)`-dimensional Euclidean Hausdorff
measure.  The proof transports the compact facet through the affine-space
translation isometry to the facet-span direction, where the corresponding
Hausdorff measure is volume and is finite on compact sets.
-/
theorem geometricSimplexFacetInSpan_euclideanHausdorffMeasure_lt_top
    {d : Nat} [NeZero d]
    (s : GeometricSimplex d) (i : Fin (d + 1)) :
    (μHE[d - 1] : Measure (geometricSimplexFacetSpan s i))
        (geometricSimplexFacetInSpan s i).closedInterior < ⊤ := by
  let p : geometricSimplexFacetSpan s i :=
    Classical.choice (geometricSimplexFacetSpan_nonempty s i)
  have hpres :
      MeasurePreserving (IsometryEquiv.vaddConst p)
        (volume : Measure (geometricSimplexFacetSpan s i).direction)
        (μHE[d - 1] : Measure (geometricSimplexFacetSpan s i)) := by
    simpa only [geometricSimplexFacetSpan_finrank s i] using
      (EuclideanGeometry.measurePreserving_vaddConst p)
  rw [← hpres.measure_preimage_equiv
    (geometricSimplexFacetInSpan s i).closedInterior]
  have hcompact :
      IsCompact ((IsometryEquiv.vaddConst p) ⁻¹'
        (geometricSimplexFacetInSpan s i).closedInterior) := by
    exact (IsometryEquiv.vaddConst p).toHomeomorph.isCompact_preimage.2
      (geometricSimplexFacetInSpan_compact s i)
  exact hcompact.measure_lt_top

/--
The ambient `(d - 1)`-dimensional Euclidean Hausdorff measure of an opposite
facet is finite.  This follows from intrinsic finiteness plus invariance under
the affine-subspace isometric inclusion.
-/
theorem geometricSimplexFacet_euclideanHausdorffMeasure_lt_top
    {d : Nat} [NeZero d]
    (s : GeometricSimplex d) (i : Fin (d + 1)) :
    (μHE[d - 1] : Measure (GeometricSimplexPoint d))
        (geometricSimplexFacet s i) < ⊤ := by
  rw [← geometricSimplexFacetInSpan_image s i,
    AffineSubspace.euclideanHausdorffMeasure_coe_image]
  exact geometricSimplexFacetInSpan_euclideanHausdorffMeasure_lt_top s i

/-- Euclidean codimension-one surface measure restricted to one simplex facet. -/
noncomputable def geometricSimplexFacetSurfaceMeasure
    {d : Nat} [NeZero d]
    (s : GeometricSimplex d) (i : Fin (d + 1)) :
    Measure (GeometricSimplexPoint d) :=
  (μHE[d - 1] : Measure (GeometricSimplexPoint d)).restrict
    (geometricSimplexFacet s i)

/-- The restricted simplex-facet surface measure is a finite measure. -/
instance geometricSimplexFacetSurfaceMeasure_isFinite
    {d : Nat} [NeZero d]
    (s : GeometricSimplex d) (i : Fin (d + 1)) :
    IsFiniteMeasure (geometricSimplexFacetSurfaceMeasure s i) := by
  rw [geometricSimplexFacetSurfaceMeasure, isFiniteMeasure_restrict]
  exact (geometricSimplexFacet_euclideanHausdorffMeasure_lt_top s i).ne

end

end Continuum

end CACEFormal
