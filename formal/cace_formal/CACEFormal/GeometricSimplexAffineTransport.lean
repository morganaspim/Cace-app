import Mathlib
import CACEFormal.ReferenceSimplexGeometry
import CACEFormal.ReferenceSimplexCell

namespace CACEFormal

open Set
open scoped BigOperators RealInnerProductSpace

namespace Continuum

noncomputable section

/-!
# Canonical affine transport from the reference simplex

Every full-dimensional geometric simplex has vertices forming an affine basis.
After singling out vertex zero, the remaining edge vectors form a linear basis
of the Euclidean ambient space.

This module combines that Mathlib affine-basis structure with the canonical
reference simplex to construct a certified affine equivalence

  T_s : Δ_ref ≃ᵃ s

whose linear part sends each reference basis vector `e_i` to the target edge
`s.points i.succ - s.points 0`.

No Piola or PDE claim is made here.  This is the geometry transport layer that
later P1 and RT0 proofs can share.
-/

/-- A full-dimensional geometric simplex is an affine basis of its Euclidean ambient. -/
noncomputable def geometricSimplexAffineBasis
    {d : Nat} (s : GeometricSimplex d) :
    AffineBasis (Fin (d + 1)) ℝ (EuclideanDomain d) where
  toFun := s.points
  ind' := s.independent
  tot' := s.span_eq_top (by simp [EuclideanDomain])

@[simp]
theorem geometricSimplexAffineBasis_apply
    {d : Nat} (s : GeometricSimplex d) (j : Fin (d + 1)) :
    geometricSimplexAffineBasis s j = s.points j := rfl

/--
The target edge basis based at vertex zero, reindexed canonically by `Fin d`.
-/
noncomputable def geometricSimplexEdgeBasis
    {d : Nat} (s : GeometricSimplex d) :
    Basis (Fin d) ℝ (EuclideanDomain d) :=
  ((geometricSimplexAffineBasis s).basisOf (0 : Fin (d + 1))).reindex
    (referenceSimplexNonzeroEquiv d).symm

@[simp]
theorem geometricSimplexEdgeBasis_apply
    {d : Nat} (s : GeometricSimplex d) (i : Fin d) :
    geometricSimplexEdgeBasis s i =
      s.points i.succ -ᵥ s.points 0 := by
  simp [geometricSimplexEdgeBasis, referenceSimplexNonzeroEquiv,
    AffineBasis.basisOf_apply, geometricSimplexAffineBasis]

/-- The standard Euclidean coordinate basis in the CACE ambient. -/
noncomputable def referenceEuclideanBasis (d : Nat) :
    Basis (Fin d) ℝ (EuclideanDomain d) :=
  PiLp.basisFun 2 ℝ (Fin d)

@[simp]
theorem referenceEuclideanBasis_apply
    {d : Nat} (i : Fin d) :
    referenceEuclideanBasis d i = basisVector i := by
  simp [referenceEuclideanBasis, basisVector]

/--
Canonical invertible linear map carrying the standard reference edges to the
target simplex edges.
-/
noncomputable def referenceToGeometricSimplexLinearEquiv
    {d : Nat} (s : GeometricSimplex d) :
    EuclideanDomain d ≃ₗ[ℝ] EuclideanDomain d :=
  (referenceEuclideanBasis d).equiv
    (geometricSimplexEdgeBasis s) (Equiv.refl (Fin d))

@[simp]
theorem referenceToGeometricSimplexLinearEquiv_basisVector
    {d : Nat} (s : GeometricSimplex d) (i : Fin d) :
    referenceToGeometricSimplexLinearEquiv s (basisVector i) =
      s.points i.succ -ᵥ s.points 0 := by
  rw [← referenceEuclideanBasis_apply i]
  simp [referenceToGeometricSimplexLinearEquiv]

/--
Canonical affine equivalence from the reference ambient to the target simplex
ambient.  It fixes reference origin as target vertex zero and uses the certified
edge-basis linear equivalence.
-/
noncomputable def referenceToGeometricSimplexAffineEquiv
    {d : Nat} (s : GeometricSimplex d) :
    EuclideanDomain d ≃ᵃ[ℝ] EuclideanDomain d :=
  AffineEquiv.ofLinearEquiv
    (referenceToGeometricSimplexLinearEquiv s)
    0
    (s.points 0)

@[simp]
theorem referenceToGeometricSimplexAffineEquiv_zero
    {d : Nat} (s : GeometricSimplex d) :
    referenceToGeometricSimplexAffineEquiv s 0 = s.points 0 := by
  simp [referenceToGeometricSimplexAffineEquiv,
    AffineEquiv.ofLinearEquiv_apply]

@[simp]
theorem referenceToGeometricSimplexAffineEquiv_basisVector
    {d : Nat} (s : GeometricSimplex d) (i : Fin d) :
    referenceToGeometricSimplexAffineEquiv s (basisVector i) =
      s.points i.succ := by
  rw [referenceToGeometricSimplexAffineEquiv,
    AffineEquiv.ofLinearEquiv_apply]
  simp [referenceToGeometricSimplexLinearEquiv_basisVector]

/-- The affine transport maps every reference vertex to the matching target vertex. -/
@[simp]
theorem referenceToGeometricSimplexAffineEquiv_vertex
    {d : Nat} (s : GeometricSimplex d) (j : Fin (d + 1)) :
    referenceToGeometricSimplexAffineEquiv s
        ((referenceGeometricSimplex d).points j) =
      s.points j := by
  refine Fin.cases ?_ (fun i => ?_) j
  · simp
  · simp

/-- The transport maps the reference vertex range exactly onto the target vertex range. -/
theorem referenceToGeometricSimplexAffineEquiv_image_vertices
    {d : Nat} (s : GeometricSimplex d) :
    referenceToGeometricSimplexAffineEquiv s ''
        Set.range (referenceGeometricSimplex d).points =
      Set.range s.points := by
  ext x
  constructor
  · rintro ⟨y, ⟨j, rfl⟩, rfl⟩
    exact ⟨j, referenceToGeometricSimplexAffineEquiv_vertex s j⟩
  · rintro ⟨j, rfl⟩
    refine ⟨(referenceGeometricSimplex d).points j, ⟨j, rfl⟩, ?_⟩
    exact referenceToGeometricSimplexAffineEquiv_vertex s j

/-- The affine transport carries the whole reference simplex cell onto the target simplex cell. -/
theorem referenceToGeometricSimplexAffineEquiv_image_cell
    {d : Nat} (s : GeometricSimplex d) :
    referenceToGeometricSimplexAffineEquiv s ''
        geometricSimplexCell (referenceGeometricSimplex d) =
      geometricSimplexCell s := by
  rw [geometricSimplexCell_eq_convexHull,
    geometricSimplexCell_eq_convexHull]
  rw [AffineMap.image_convexHull]
  rw [referenceToGeometricSimplexAffineEquiv_image_vertices]

/-- Equivalent formulation using the inequality-defined reference simplex. -/
theorem referenceToGeometricSimplexAffineEquiv_image_referenceSimplex
    {d : Nat} (s : GeometricSimplex d) :
    referenceToGeometricSimplexAffineEquiv s ''
        euclideanReferenceSimplex d =
      geometricSimplexCell s := by
  rw [← referenceGeometricSimplex_cell_eq_referenceSimplex d]
  exact referenceToGeometricSimplexAffineEquiv_image_cell s

end

end Continuum

end CACEFormal
