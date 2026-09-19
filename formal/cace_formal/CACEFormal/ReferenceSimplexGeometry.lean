import Mathlib
import CACEFormal.ReferenceSimplexIntegrability
import CACEFormal.SimplexFacetGeometry

namespace CACEFormal

open Set
open scoped BigOperators RealInnerProductSpace

namespace Continuum

noncomputable section

/-!
# Geometric realization of the Euclidean reference simplex

The analytic reference simplex used by the fiber/Fubini track is

  Δ_d = {x : ℝ^d | 0 ≤ x_j, Σ_j x_j ≤ 1}.

This module packages the canonical vertices
  0, e_0, ..., e_{d-1}
as a genuine `GeometricSimplex d`.  The affine-independence proof is reduced
to Mathlib's certified orthonormality of the Euclidean coordinate vectors.

Later modules identify its closed cell and opposite facets with the explicit
coordinate inequalities already used by the fiber calculus.
-/

/-- Canonical vertex family: vertex zero is the origin, and successor vertices are basis vectors. -/
noncomputable def referenceSimplexVertex {d : Nat} :
    Fin (d + 1) → EuclideanDomain d :=
  Fin.cases 0 (fun j : Fin d => basisVector j)

@[simp]
theorem referenceSimplexVertex_zero {d : Nat} :
    referenceSimplexVertex (d := d) 0 = 0 := rfl

@[simp]
theorem referenceSimplexVertex_succ {d : Nat} (j : Fin d) :
    referenceSimplexVertex (d := d) j.succ = basisVector j := rfl

/--
Successor identifies `Fin d` with all nonzero vertices of `Fin (d+1)`.
This explicit equivalence is used to transport Euclidean-basis independence.
-/
def referenceSimplexNonzeroEquiv (d : Nat) :
    Fin d ≃ {j : Fin (d + 1) // j ≠ 0} where
  toFun j := ⟨j.succ, Fin.succ_ne_zero j⟩
  invFun j := j.1.pred j.2
  left_inv j := by
    simp
  right_inv j := by
    apply Subtype.ext
    exact Fin.succ_pred j.1 j.2

/-- The canonical reference-simplex vertices are affinely independent. -/
theorem referenceSimplexVertex_affineIndependent {d : Nat} :
    AffineIndependent ℝ (referenceSimplexVertex (d := d)) := by
  rw [affineIndependent_iff_linearIndependent_vsub
    ℝ (referenceSimplexVertex (d := d)) (0 : Fin (d + 1))]
  let e := referenceSimplexNonzeroEquiv d
  have hbasis :
      LinearIndependent ℝ (fun j : Fin d => basisVector j) :=
    EuclideanSpace.orthonormal_single.linearIndependent
  have hcomp :
      LinearIndependent ℝ
        ((fun j : Fin d => basisVector j) ∘ e.symm) :=
    hbasis.comp e.symm e.symm.injective
  convert hcomp using 1
  funext j
  rcases j with ⟨j, hj⟩
  obtain ⟨k, rfl⟩ := Fin.exists_succ_eq.mpr hj
  simp [referenceSimplexVertex, e, referenceSimplexNonzeroEquiv]

/-- The canonical geometric simplex with vertices `0,e_0,...,e_{d-1}`. -/
noncomputable def referenceGeometricSimplex (d : Nat) :
    GeometricSimplex d where
  points := referenceSimplexVertex
  independent := referenceSimplexVertex_affineIndependent

@[simp]
theorem referenceGeometricSimplex_points_zero (d : Nat) :
    (referenceGeometricSimplex d).points 0 = 0 := rfl

@[simp]
theorem referenceGeometricSimplex_points_succ
    {d : Nat} (j : Fin d) :
    (referenceGeometricSimplex d).points j.succ = basisVector j := rfl

end

end Continuum

end CACEFormal
