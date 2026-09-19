import CACEFormal.PositiveLaplacianAnnihilator
import CACEFormal.H1DomainBridge

namespace CACEFormal

open Set Finset MeasureTheory
open scoped BigOperators LineDeriv SchwartzMap

namespace Continuum

noncomputable section

/-!
# H(div) graph annihilator bridge

This module isolates the algebraic/elliptic heart of the remaining whole-space
H(div) density argument.

For H(div) graph data `x = (q,g)`, suppose:

* `div q = g` in tempered distributions; and
* the reversed graph datum `(g,q)` is an H1 distributional graph, so
  `∂_i g = q_i`.

Then `Δg = g`.  The positive-Laplacian annihilator proves `g = 0`, and
injectivity of the L2-to-tempered-distribution embedding then gives `q = 0`.

The remaining density step is therefore reduced to proving that orthogonality
to every Schwartz H(div) graph field implies membership of the reversed H1
graph.
-/

/-- Reinterpret H(div) coordinates `(q,g)` as candidate H1 coordinates
`(g,q)`. -/
def reversedHDivGraph {n : Nat}
    (x : HDivComplexGraphAmbient n) : H1ComplexGraphAmbient n :=
  (x.2, x.1)

/-- The canonical L2 embedding into tempered distributions is injective. -/
theorem complexL2ToDistribution_injective (n : Nat) :
    Function.Injective (complexL2ToDistribution n) := by
  change Function.Injective ⇑(complexL2ToDistribution n).toLinearMap
  rw [← LinearMap.ker_eq_bot]
  simpa [complexL2ToDistribution] using
    (MeasureTheory.Lp.ker_toTemperedDistributionCLM_eq_bot
      (E := EuclideanDomain n) (F := ℂ)
      (μ := volume) (p := (2 : ENNReal)))

/-- If an H(div) graph and its reversed coordinates satisfy the H1 graph
relation, then the divergence coordinate solves `Δg = g`. -/
theorem laplacian_divCoordinate_eq_self_of_reversedH1
    (n : Nat) (x : HDivComplexGraphAmbient n)
    (hdiv : x ∈ HDivDistributionalGraphSubmodule n)
    (hrev : reversedHDivGraph x ∈ H1DistributionalGraphSubmodule n) :
    Laplacian.laplacian (complexL2ToDistribution n x.2) =
      complexL2ToDistribution n x.2 := by
  have hgrad :
      ∀ i : Fin n,
        weakPartial i (complexL2ToDistribution n x.2) =
          complexL2ToDistribution n (x.1 i) := by
    simpa [reversedHDivGraph] using
      (mem_H1DistributionalGraphSubmodule_iff n (reversedHDivGraph x)).mp hrev
  have hdivEq :
      distributionalDivergence (complexGraphFieldDistribution x) =
        complexL2ToDistribution n x.2 :=
    (mem_HDivDistributionalGraphSubmodule_iff n x).mp hdiv
  rw [TemperedDistribution.laplacian_eq_sum
    (EuclideanSpace.basisFun (Fin n) ℝ)]
  simp only [EuclideanSpace.basisFun_apply]
  change
    (∑ i : Fin n,
      weakPartial i (weakPartial i (complexL2ToDistribution n x.2))) =
      complexL2ToDistribution n x.2
  calc
    (∑ i : Fin n,
      weakPartial i (weakPartial i (complexL2ToDistribution n x.2))) =
        ∑ i : Fin n,
          weakPartial i (complexL2ToDistribution n (x.1 i)) := by
      apply Finset.sum_congr rfl
      intro i _hi
      rw [hgrad i]
    _ = distributionalDivergence (complexGraphFieldDistribution x) := by
      rfl
    _ = complexL2ToDistribution n x.2 := hdivEq

/-- H(div) plus reversed-H1 compatibility has only the zero graph datum. -/
theorem hdivGraph_eq_zero_of_reversedH1
    (n : Nat) (x : HDivComplexGraphAmbient n)
    (hdiv : x ∈ HDivDistributionalGraphSubmodule n)
    (hrev : reversedHDivGraph x ∈ H1DistributionalGraphSubmodule n) :
    x = 0 := by
  have hgDist :
      complexL2ToDistribution n x.2 = 0 :=
    laplacian_eq_self_imp_eq_zero
      (complexL2ToDistribution n x.2)
      (laplacian_divCoordinate_eq_self_of_reversedH1 n x hdiv hrev)
  have hg : x.2 = 0 := by
    apply complexL2ToDistribution_injective n
    simpa using hgDist
  have hgrad :=
    (mem_H1DistributionalGraphSubmodule_iff n (reversedHDivGraph x)).mp hrev
  have hq : x.1 = 0 := by
    funext i
    apply complexL2ToDistribution_injective n
    have hi := hgrad i
    change
      weakPartial i (complexL2ToDistribution n x.2) =
        complexL2ToDistribution n (x.1 i) at hi
    rw [hg] at hi
    simpa using hi.symm
  apply Prod.ext
  · exact hq
  · exact hg

end

end Continuum

end CACEFormal
