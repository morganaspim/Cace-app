import Mathlib
import CACEFormal.ContinuumSobolev

namespace CACEFormal

open Set
open scoped BigOperators

namespace Continuum

noncomputable section

/-!
# Coordinate fibers of the Euclidean reference simplex

For the local Gauss--Green proof we use the reference simplex
  Δ_d = {x : ℝ^d | 0 ≤ x_j for every j and Σ_j x_j ≤ 1}.

The main theorem below gives the exact Fubini slice in any coordinate: after
the other coordinates are fixed, the selected coordinate ranges over
`[0, 1 - Σ_{j ≠ i} x_j]`.  This is the algebraic domain decomposition needed
to reduce the local simplex integration-by-parts identity to the one-dimensional
fundamental theorem / interval integration by parts.
-/

/-- The closed reference simplex in the canonical Euclidean Sobolev ambient. -/
def euclideanReferenceSimplex (d : Nat) : Set (EuclideanDomain d) :=
  {x |
    (∀ j : Fin d, 0 ≤ EuclideanSpace.proj j x) ∧
      (∑ j : Fin d, EuclideanSpace.proj j x) ≤ 1}

/-- Sum of all coordinates except the selected fiber coordinate. -/
def referenceSimplexOtherCoordinateSum {d : Nat}
    (i : Fin d) (x : EuclideanDomain d) : ℝ :=
  ∑ j ∈ Finset.univ.erase i, EuclideanSpace.proj j x

/-- Upper endpoint of the selected coordinate fiber. -/
def referenceSimplexFiberUpper {d : Nat}
    (i : Fin d) (x : EuclideanDomain d) : ℝ :=
  1 - referenceSimplexOtherCoordinateSum i x

/-- Splitting the total coordinate sum into all coordinates except `i`, plus `i`. -/
theorem referenceSimplex_coordinate_sum_split {d : Nat}
    (i : Fin d) (x : EuclideanDomain d) :
    referenceSimplexOtherCoordinateSum i x + EuclideanSpace.proj i x =
      ∑ j : Fin d, EuclideanSpace.proj j x := by
  simpa [referenceSimplexOtherCoordinateSum] using
    (Finset.sum_erase_add Finset.univ
      (fun j : Fin d => EuclideanSpace.proj j x) (Finset.mem_univ i))

/--
Exact coordinate-fiber characterization of the reference simplex.

The data on the right says:
* every non-fiber coordinate is nonnegative;
* the fiber coordinate lies in the interval from zero to the remaining mass.
-/
theorem mem_euclideanReferenceSimplex_iff_fiber
    {d : Nat} (i : Fin d) (x : EuclideanDomain d) :
    x ∈ euclideanReferenceSimplex d ↔
      (∀ j ∈ Finset.univ.erase i, 0 ≤ EuclideanSpace.proj j x) ∧
        EuclideanSpace.proj i x ∈
          Set.Icc 0 (referenceSimplexFiberUpper i x) := by
  constructor
  · intro hx
    refine ⟨?_, ?_⟩
    · intro j hj
      exact hx.1 j
    · refine ⟨hx.1 i, ?_⟩
      have hsum :
          referenceSimplexOtherCoordinateSum i x +
              EuclideanSpace.proj i x ≤ 1 := by
        rw [referenceSimplex_coordinate_sum_split i x]
        exact hx.2
      change EuclideanSpace.proj i x ≤
        1 - referenceSimplexOtherCoordinateSum i x
      exact (le_sub_iff_add_le').2 hsum
  · rintro ⟨hother, hi⟩
    refine ⟨?_, ?_⟩
    · intro j
      by_cases hji : j = i
      · simpa [hji] using hi.1
      · exact hother j (Finset.mem_erase.mpr ⟨hji, Finset.mem_univ j⟩)
    · have hi_upper :
          EuclideanSpace.proj i x ≤
            1 - referenceSimplexOtherCoordinateSum i x := by
        simpa [referenceSimplexFiberUpper] using hi.2
      have hsum :
          referenceSimplexOtherCoordinateSum i x +
              EuclideanSpace.proj i x ≤ 1 :=
        (le_sub_iff_add_le').1 hi_upper
      rw [← referenceSimplex_coordinate_sum_split i x]
      exact hsum

/-- A nonempty reference-simplex fiber necessarily has a nonnegative upper endpoint. -/
theorem referenceSimplexFiberUpper_nonneg_of_mem
    {d : Nat} (i : Fin d) {x : EuclideanDomain d}
    (hx : x ∈ euclideanReferenceSimplex d) :
    0 ≤ referenceSimplexFiberUpper i x := by
  have hi := (mem_euclideanReferenceSimplex_iff_fiber i x).mp hx
  exact hi.2.1.trans hi.2.2

end

end Continuum

end CACEFormal
