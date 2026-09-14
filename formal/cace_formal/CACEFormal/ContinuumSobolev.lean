import Mathlib.Analysis.Distribution.Sobolev
import Mathlib.Analysis.InnerProductSpace.PiL2

namespace CACEFormal

open scoped BigOperators LineDeriv SchwartzMap

namespace Continuum

/-- Whole-space finite-dimensional Euclidean domain used by the continuum closure track. -/
abbrev EuclideanDomain (n : Nat) := EuclideanSpace ℝ (Fin n)

/-- Scalar tempered distributions on Euclidean `ℝⁿ`. -/
abbrev ScalarDistribution (n : Nat) := 𝓢'(EuclideanDomain n, ℂ)

/-- Vector-valued distribution represented componentwise. -/
abbrev VectorDistribution (n : Nat) := Fin n → ScalarDistribution n

/-- Canonical Euclidean basis vector `eᵢ`. -/
noncomputable def basisVector {n : Nat} (i : Fin n) : EuclideanDomain n :=
  EuclideanSpace.single i (1 : ℝ)

/-- Actual Mathlib Bessel-potential `H¹ = H^{1,2}` membership. -/
def InH1 {n : Nat} (u : ScalarDistribution n) : Prop :=
  TemperedDistribution.MemSobolev (E := EuclideanDomain n) (F := ℂ) (1 : ℝ) 2 u

/-- Actual Mathlib `L² = H^{0,2}` membership for a tempered distribution. -/
def InL2 {n : Nat} (u : ScalarDistribution n) : Prop :=
  TemperedDistribution.MemSobolev (E := EuclideanDomain n) (F := ℂ) (0 : ℝ) 2 u

/-- Distributional coordinate derivative in direction `eᵢ`. -/
noncomputable def weakPartial {n : Nat} (i : Fin n)
    (u : ScalarDistribution n) : ScalarDistribution n :=
  ∂_{basisVector i} u

/-- Distributional divergence of a componentwise vector distribution. -/
noncomputable def distributionalDivergence {n : Nat}
    (q : VectorDistribution n) : ScalarDistribution n :=
  ∑ i : Fin n, weakPartial i (q i)

/--
Whole-space distributional `H(div)` predicate: every component is `L²` and the
distributional divergence is `L²`.

This is a genuine Sobolev/distributional interface. It is deliberately not yet a
bounded-domain normal-trace space; that boundary layer is the v3.27 target.
-/
def InHDiv {n : Nat} (q : VectorDistribution n) : Prop :=
  (∀ i : Fin n, InL2 (q i)) ∧ InL2 (distributionalDivergence q)

/-- Mathlib's Sobolev derivative theorem gives every weak coordinate derivative of an H¹ field in L². -/
theorem h1_weakPartial_l2 {n : Nat} {u : ScalarDistribution n}
    (hu : InH1 u) (i : Fin n) : InL2 (weakPartial i u) := by
  change TemperedDistribution.MemSobolev
    (E := EuclideanDomain n) (F := ℂ) (1 : ℝ) 2 u at hu
  change TemperedDistribution.MemSobolev
    (E := EuclideanDomain n) (F := ℂ) (0 : ℝ) 2 (weakPartial i u)
  have hder := TemperedDistribution.MemSobolev.lineDerivOp
    (E := EuclideanDomain n) (F := ℂ) hu (m := basisVector i)
  simpa [weakPartial] using hder

/-- H¹ membership also implies L² membership by monotonicity of Sobolev order. -/
theorem h1_l2 {n : Nat} {u : ScalarDistribution n} (hu : InH1 u) : InL2 u := by
  change TemperedDistribution.MemSobolev
    (E := EuclideanDomain n) (F := ℂ) (1 : ℝ) 2 u at hu
  change TemperedDistribution.MemSobolev
    (E := EuclideanDomain n) (F := ℂ) (0 : ℝ) 2 u
  exact TemperedDistribution.MemSobolev.mono
    (E := EuclideanDomain n) (F := ℂ) (s := (1 : ℝ)) (s' := (0 : ℝ))
    (by norm_num) hu

/-- Extract the componentwise L² statement from the H(div) interface. -/
theorem hdiv_component_l2 {n : Nat} {q : VectorDistribution n}
    (hq : InHDiv q) (i : Fin n) : InL2 (q i) :=
  hq.1 i

/-- Extract the L² distributional-divergence statement from the H(div) interface. -/
theorem hdiv_divergence_l2 {n : Nat} {q : VectorDistribution n}
    (hq : InHDiv q) : InL2 (distributionalDivergence q) :=
  hq.2

end Continuum

end CACEFormal
