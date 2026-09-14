import CACEFormal.Sobolev2Model
import Mathlib.Analysis.Distribution.SchwartzSpace.Deriv
import Mathlib.Topology.UniformSpace.Completion

namespace CACEFormal

open MeasureTheory Finset
open scoped BigOperators LineDeriv SchwartzMap

namespace Continuum

/-- Real whole-space `L²` used by the graph-norm closure models. -/
abbrev RealL2 (n : Nat) :=
  Lp ℝ 2 (volume : Measure (EuclideanDomain n))

/-- A smooth scalar core field. -/
abbrev SmoothScalar (n : Nat) := 𝓢(EuclideanDomain n, ℝ)

/-- A smooth vector core field. -/
abbrev SmoothVector (n : Nat) := Fin n → SmoothScalar n

/-- Ambient graph data `(u, ∇u)` for the H¹ graph norm. -/
abbrev H1GraphAmbient (n : Nat) := RealL2 n × (Fin n → RealL2 n)

/-- Ambient graph data `(q, div q)` for the H(div) graph norm. -/
abbrev HDivGraphAmbient (n : Nat) := (Fin n → RealL2 n) × RealL2 n

/-- Real Schwartz-to-L² map at the pinned measure. -/
noncomputable def schwartzRealL2 (n : Nat) :
    SmoothScalar n →L[ℝ] RealL2 n :=
  SchwartzMap.toLpCLM ℝ ℝ 2 volume

/-- Smooth scalar graph map `u ↦ (u, (∂ᵢu)ᵢ)`. -/
noncomputable def smoothH1GraphMap (n : Nat) :
    SmoothScalar n →ₗ[ℝ] H1GraphAmbient n where
  toFun u :=
    (schwartzRealL2 n u,
      fun i => schwartzRealL2 n (∂_{basisVector i} u))
  map_add' u v := by
    apply Prod.ext
    · simp [schwartzRealL2]
    · funext i
      simp [schwartzRealL2]
  map_smul' c u := by
    apply Prod.ext
    · simp [schwartzRealL2]
    · funext i
      simp [schwartzRealL2]

/-- Smooth vector graph map `q ↦ ((qᵢ)ᵢ, ∑ᵢ ∂ᵢqᵢ)`. -/
noncomputable def smoothHDivGraphMap (n : Nat) :
    SmoothVector n →ₗ[ℝ] HDivGraphAmbient n where
  toFun q :=
    (fun i => schwartzRealL2 n (q i),
      ∑ i : Fin n, schwartzRealL2 n (∂_{basisVector i} (q i)))
  map_add' q r := by
    apply Prod.ext
    · funext i
      simp [schwartzRealL2]
    · simp [schwartzRealL2, Finset.sum_add_distrib]
  map_smul' c q := by
    apply Prod.ext
    · funext i
      simp [schwartzRealL2]
    · simp [schwartzRealL2, Finset.smul_sum]

/-- The smooth H¹ graph core as an honest normed subspace of graph data. -/
noncomputable def H1SmoothGraphCore (n : Nat) : Submodule ℝ (H1GraphAmbient n) :=
  LinearMap.range (smoothH1GraphMap n)

/-- The smooth H(div) graph core as an honest normed subspace of graph data. -/
noncomputable def HDivSmoothGraphCore (n : Nat) : Submodule ℝ (HDivGraphAmbient n) :=
  LinearMap.range (smoothHDivGraphMap n)

/--
H¹ graph completion: the completion of smooth scalar fields in the `(u, ∇u)` graph norm.
This definition makes the density statement constructive rather than an assumption.
-/
abbrev H1GraphCompletion (n : Nat) :=
  UniformSpace.Completion (H1SmoothGraphCore n)

/--
H(div) graph completion: the completion of smooth vector fields in the `(q, div q)` graph norm.
This is the standard closed-graph completion model; equivalence with the distributional predicate
`InHDiv` is kept as a separate bridge theorem rather than being silently assumed.
-/
abbrev HDivGraphCompletion (n : Nat) :=
  UniformSpace.Completion (HDivSmoothGraphCore n)

/-- Smooth scalar graph fields are dense in the H¹ graph completion by construction. -/
theorem denseRange_H1SmoothGraphCore (n : Nat) :
    DenseRange ((↑) : H1SmoothGraphCore n → H1GraphCompletion n) :=
  UniformSpace.Completion.denseRange_coe

/-- Smooth vector graph fields are dense in the H(div) graph completion by construction. -/
theorem denseRange_HDivSmoothGraphCore (n : Nat) :
    DenseRange ((↑) : HDivSmoothGraphCore n → HDivGraphCompletion n) :=
  UniformSpace.Completion.denseRange_coe

end Continuum

end CACEFormal
