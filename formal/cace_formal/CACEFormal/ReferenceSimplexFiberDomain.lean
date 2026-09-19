import Mathlib
import CACEFormal.ReferenceSimplexFiberMeasure

namespace CACEFormal

open Set MeasureTheory
open scoped BigOperators MeasureTheory

namespace Continuum

noncomputable section

/-!
# Base domain for reference-simplex coordinate fibers

The orthogonal hyperplane contains many lines parallel to the selected
coordinate axis, but only some intersect the reference simplex.  This module
identifies exactly those base points.

For a base point `y ∈ (ℝ ∙ e_i)ᗮ`, the selected coordinate is already zero.
Thus the fiber is nonempty precisely when:

* every nonselected coordinate of `y` is nonnegative;
* their sum is at most one.

For such a base point the simplex indicator along the line is exactly the
indicator of the scalar interval `[0, referenceSimplexFiberUpper i y]`.
-/

/-- Orthogonal base points whose coordinate fiber meets the reference simplex. -/
def referenceSimplexFiberBaseDomain {d : Nat} (i : Fin d) :
    Set ((referenceSimplexCoordinateLine i)ᗮ) :=
  {y |
    (∀ j ∈ Finset.univ.erase i,
      0 ≤ EuclideanSpace.proj j (y : EuclideanDomain d)) ∧
    referenceSimplexOtherCoordinateSum i (y : EuclideanDomain d) ≤ 1}

/-- The upper fiber endpoint is nonnegative exactly on the admissible base domain. -/
theorem referenceSimplexFiberUpper_nonneg_of_baseDomain
    {d : Nat} (i : Fin d)
    {y : (referenceSimplexCoordinateLine i)ᗮ}
    (hy : y ∈ referenceSimplexFiberBaseDomain i) :
    0 ≤ referenceSimplexFiberUpper i (y : EuclideanDomain d) := by
  unfold referenceSimplexFiberBaseDomain at hy
  unfold referenceSimplexFiberUpper
  linarith [hy.2]

/-- An admissible orthogonal base point itself belongs to the reference simplex. -/
theorem referenceSimplexFiberBaseDomain_mem_simplex
    {d : Nat} (i : Fin d)
    {y : (referenceSimplexCoordinateLine i)ᗮ}
    (hy : y ∈ referenceSimplexFiberBaseDomain i) :
    (y : EuclideanDomain d) ∈ euclideanReferenceSimplex d := by
  rw [mem_euclideanReferenceSimplex_iff_fiber i]
  refine ⟨hy.1, ?_⟩
  have hyi : EuclideanSpace.proj i (y : EuclideanDomain d) = 0 :=
    (mem_referenceSimplexCoordinateLine_orthogonal_iff
      i (y : EuclideanDomain d)).mp y.property
  rw [hyi]
  exact ⟨le_rfl, referenceSimplexFiberUpper_nonneg_of_baseDomain i hy⟩

/-- Conversely, an orthogonal point in the reference simplex is an admissible base point. -/
theorem mem_referenceSimplexFiberBaseDomain_of_mem_simplex
    {d : Nat} (i : Fin d)
    {y : (referenceSimplexCoordinateLine i)ᗮ}
    (hy : (y : EuclideanDomain d) ∈ euclideanReferenceSimplex d) :
    y ∈ referenceSimplexFiberBaseDomain i := by
  have hf := (mem_euclideanReferenceSimplex_iff_fiber i
    (y : EuclideanDomain d)).mp hy
  refine ⟨hf.1, ?_⟩
  have hupper : 0 ≤ referenceSimplexFiberUpper i (y : EuclideanDomain d) := by
    exact hf.2.1.trans hf.2.2
  unfold referenceSimplexFiberUpper at hupper
  linarith

/-- Exact characterization of the admissible orthogonal base domain. -/
theorem mem_referenceSimplexFiberBaseDomain_iff
    {d : Nat} (i : Fin d)
    (y : (referenceSimplexCoordinateLine i)ᗮ) :
    y ∈ referenceSimplexFiberBaseDomain i ↔
      (y : EuclideanDomain d) ∈ euclideanReferenceSimplex d :=
  ⟨referenceSimplexFiberBaseDomain_mem_simplex i,
    mem_referenceSimplexFiberBaseDomain_of_mem_simplex i⟩

/--
A coordinate fiber through an orthogonal base point meets the reference simplex
exactly when the base is admissible and the scalar parameter lies in its
closed fiber interval.
-/
theorem referenceSimplexFiberPoint_mem_iff_baseDomain
    {d : Nat} (i : Fin d)
    (y : (referenceSimplexCoordinateLine i)ᗮ) (t : ℝ) :
    referenceSimplexFiberPoint i (y : EuclideanDomain d) t ∈
        euclideanReferenceSimplex d ↔
      y ∈ referenceSimplexFiberBaseDomain i ∧
        t ∈ Set.Icc 0
          (referenceSimplexFiberUpper i (y : EuclideanDomain d)) := by
  constructor
  · intro h
    have hf := (mem_euclideanReferenceSimplex_iff_fiber i
      (referenceSimplexFiberPoint i (y : EuclideanDomain d) t)).mp h
    have hother :
        ∀ j ∈ Finset.univ.erase i,
          0 ≤ EuclideanSpace.proj j (y : EuclideanDomain d) := by
      intro j hj
      rw [← referenceSimplexFiberPoint_proj_ne
        i j (y : EuclideanDomain d) t (Finset.mem_erase.mp hj).1]
      exact hf.1 j hj
    have ht :
        t ∈ Set.Icc 0
          (referenceSimplexFiberUpper i (y : EuclideanDomain d)) := by
      simpa using hf.2
    have hsum :
        referenceSimplexOtherCoordinateSum i (y : EuclideanDomain d) ≤ 1 := by
      have hup : 0 ≤
          referenceSimplexFiberUpper i (y : EuclideanDomain d) :=
        ht.1.trans ht.2
      unfold referenceSimplexFiberUpper at hup
      linarith
    exact ⟨⟨hother, hsum⟩, ht⟩
  · rintro ⟨hy, ht⟩
    exact
      (referenceSimplexFiberPoint_mem_iff
        i (y : EuclideanDomain d) t hy.1).2 ht

/--
Pointwise indicator reduction along a coordinate fiber.

The multidimensional simplex indicator becomes the scalar interval indicator
when the orthogonal base point is admissible, and is identically zero
otherwise.
-/
theorem euclideanReferenceSimplex_indicator_fiber
    {d : Nat} {F : Type*} [Zero F]
    (i : Fin d) (f : EuclideanDomain d → F)
    (y : (referenceSimplexCoordinateLine i)ᗮ) (t : ℝ) :
    (euclideanReferenceSimplex d).indicator f
        (referenceSimplexFiberPoint i (y : EuclideanDomain d) t) =
      (referenceSimplexFiberBaseDomain i).indicator
        (fun y =>
          (Set.Icc 0
              (referenceSimplexFiberUpper i (y : EuclideanDomain d))).indicator
            (fun t =>
              f (referenceSimplexFiberPoint i
                (y : EuclideanDomain d) t)) t) y := by
  by_cases hy : y ∈ referenceSimplexFiberBaseDomain i
  · rw [Set.indicator_of_mem hy]
    by_cases ht :
        t ∈ Set.Icc 0
          (referenceSimplexFiberUpper i (y : EuclideanDomain d))
    · rw [Set.indicator_of_mem ht]
      rw [Set.indicator_of_mem
        ((referenceSimplexFiberPoint_mem_iff_baseDomain i y t).2
          ⟨hy, ht⟩)]
    · rw [Set.indicator_of_notMem ht]
      rw [Set.indicator_of_notMem]
      exact fun h =>
        ht ((referenceSimplexFiberPoint_mem_iff_baseDomain i y t).1 h).2
  · rw [Set.indicator_of_notMem hy]
    rw [Set.indicator_of_notMem]
    exact fun h =>
      hy ((referenceSimplexFiberPoint_mem_iff_baseDomain i y t).1 h).1

end

end Continuum

end CACEFormal
