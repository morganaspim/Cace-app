import Mathlib
import CACEFormal.ReferenceSimplexGeometry

namespace CACEFormal

open Set
open scoped BigOperators

namespace Continuum

noncomputable section

/-!
# Closed cell and facets of the geometric reference simplex

This module identifies the geometric simplex with vertices
`0,e_0,...,e_{d-1}` with the inequality-defined reference simplex used by the
fiber/Fubini proof.

The proof uses explicit barycentric weights:
* vertex 0 has weight `1 - Σ_j x_j`;
* vertex `j.succ` has weight `x_j`.

This also exposes the exact weights needed to identify opposite facets in the
next layer.
-/

/-- Canonical barycentric weights of a point relative to the reference vertices. -/
def referenceSimplexBarycentricWeight {d : Nat}
    (x : EuclideanDomain d) : Fin (d + 1) → ℝ :=
  Fin.cases
    (1 - ∑ j : Fin d, EuclideanSpace.proj j x)
    (fun j : Fin d => EuclideanSpace.proj j x)

@[simp]
theorem referenceSimplexBarycentricWeight_zero
    {d : Nat} (x : EuclideanDomain d) :
    referenceSimplexBarycentricWeight x 0 =
      1 - ∑ j : Fin d, EuclideanSpace.proj j x := rfl

@[simp]
theorem referenceSimplexBarycentricWeight_succ
    {d : Nat} (x : EuclideanDomain d) (j : Fin d) :
    referenceSimplexBarycentricWeight x j.succ =
      EuclideanSpace.proj j x := rfl

/-- The canonical reference-simplex barycentric weights always sum to one. -/
theorem referenceSimplexBarycentricWeight_sum
    {d : Nat} (x : EuclideanDomain d) :
    ∑ i : Fin (d + 1), referenceSimplexBarycentricWeight x i = 1 := by
  rw [Fin.sum_univ_succ]
  simp [referenceSimplexBarycentricWeight]

/--
For arbitrary weights summing to one, coordinate `j` of the corresponding
reference-vertex affine combination is exactly the successor weight `w (j.succ)`.
-/
theorem referenceSimplex_affineCombination_proj
    {d : Nat} (w : Fin (d + 1) → ℝ)
    (hw : ∑ i : Fin (d + 1), w i = 1)
    (j : Fin d) :
    EuclideanSpace.proj j
        (Finset.univ.affineCombination ℝ
          (referenceSimplexVertex (d := d)) w) =
      w j.succ := by
  rw [Finset.affineCombination_eq_linear_combination
    Finset.univ (referenceSimplexVertex (d := d)) w (by simpa using hw)]
  rw [Fin.sum_univ_succ]
  simp [referenceSimplexVertex, basisVector, PiLp.single_apply]

/-- The canonical barycentric affine combination reconstructs the original point. -/
theorem referenceSimplex_affineCombination_barycentric
    {d : Nat} (x : EuclideanDomain d) :
    Finset.univ.affineCombination ℝ
        (referenceSimplexVertex (d := d))
        (referenceSimplexBarycentricWeight x) = x := by
  ext j
  rw [referenceSimplex_affineCombination_proj
    (referenceSimplexBarycentricWeight x)
    (referenceSimplexBarycentricWeight_sum x) j]
  simp

/-- Every canonical barycentric weight is nonnegative for a point in the reference simplex. -/
theorem referenceSimplexBarycentricWeight_nonneg_of_mem
    {d : Nat} {x : EuclideanDomain d}
    (hx : x ∈ euclideanReferenceSimplex d)
    (i : Fin (d + 1)) :
    0 ≤ referenceSimplexBarycentricWeight x i := by
  refine Fin.cases ?_ (fun j => ?_) i
  · simp only [referenceSimplexBarycentricWeight_zero]
    linarith [hx.2]
  · simpa using hx.1 j

/-- Every canonical barycentric weight is at most one on the reference simplex. -/
theorem referenceSimplexBarycentricWeight_le_one_of_mem
    {d : Nat} {x : EuclideanDomain d}
    (hx : x ∈ euclideanReferenceSimplex d)
    (i : Fin (d + 1)) :
    referenceSimplexBarycentricWeight x i ≤ 1 := by
  refine Fin.cases ?_ (fun j => ?_) i
  · simp only [referenceSimplexBarycentricWeight_zero]
    have hsum_nonneg :
        0 ≤ ∑ k : Fin d, EuclideanSpace.proj k x :=
      Finset.sum_nonneg fun k _ => hx.1 k
    linarith
  · simp only [referenceSimplexBarycentricWeight_succ]
    have hj :
        EuclideanSpace.proj j x ≤
          ∑ k : Fin d, EuclideanSpace.proj k x :=
      Finset.single_le_sum
        (fun k _ => hx.1 k) (Finset.mem_univ j)
    exact hj.trans hx.2

/--
The geometric closed cell of the canonical simplex is exactly the
inequality-defined reference simplex used by the Fubini track.
-/
theorem referenceGeometricSimplex_cell_eq_referenceSimplex
    (d : Nat) :
    geometricSimplexCell (referenceGeometricSimplex d) =
      euclideanReferenceSimplex d := by
  ext x
  constructor
  · intro hx
    change x ∈ (referenceGeometricSimplex d).closedInterior at hx
    rcases hx with ⟨w, hw, hwIcc, hcomb⟩
    have hcoord :
        ∀ j : Fin d, EuclideanSpace.proj j x = w j.succ := by
      intro j
      rw [← hcomb]
      exact referenceSimplex_affineCombination_proj w hw j
    refine ⟨?_, ?_⟩
    · intro j
      rw [hcoord j]
      exact (hwIcc j.succ).1
    · have hsplit :
          w 0 + ∑ j : Fin d, w j.succ = 1 := by
        simpa [Fin.sum_univ_succ] using hw
      have hw0 : 0 ≤ w 0 := (hwIcc 0).1
      have hsum :
          (∑ j : Fin d, EuclideanSpace.proj j x) =
            ∑ j : Fin d, w j.succ := by
        apply Finset.sum_congr rfl
        intro j _
        exact hcoord j
      rw [hsum]
      linarith
  · intro hx
    change x ∈ (referenceGeometricSimplex d).closedInterior
    refine ⟨referenceSimplexBarycentricWeight x,
      referenceSimplexBarycentricWeight_sum x, ?_, ?_⟩
    · intro i
      exact ⟨referenceSimplexBarycentricWeight_nonneg_of_mem hx i,
        referenceSimplexBarycentricWeight_le_one_of_mem hx i⟩
    · exact referenceSimplex_affineCombination_barycentric x

end

end Continuum

end CACEFormal
