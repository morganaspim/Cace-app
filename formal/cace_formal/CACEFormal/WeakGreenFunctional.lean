import CACEFormal.BoxNormalTrace
import Mathlib.Topology.Algebra.Module.ContinuousLinearMap.Basic

namespace CACEFormal

namespace Continuum

/--
A bounded-domain Green pairing represented by two genuinely continuous bilinear maps.
`volumePairing q v` is the volume side of Green's identity and `normalTrace q v`
is its boundary functional.  The second map is therefore a bounded normal-trace
functional without requiring a pointwise boundary representative.
-/
structure BoundedGreenPairing
    (V Q : Type*)
    [NormedAddCommGroup V] [NormedSpace ℝ V]
    [NormedAddCommGroup Q] [NormedSpace ℝ Q] where
  volumePairing : Q →L[ℝ] V →L[ℝ] ℝ
  normalTrace : Q →L[ℝ] V →L[ℝ] ℝ

/-- The nested operator norm gives the canonical bilinear normal-trace bound. -/
theorem BoundedGreenPairing.normalTrace_bound
    {V Q : Type*}
    [NormedAddCommGroup V] [NormedSpace ℝ V]
    [NormedAddCommGroup Q] [NormedSpace ℝ Q]
    (G : BoundedGreenPairing V Q) (q : Q) (v : V) :
    ‖G.normalTrace q v‖ ≤ ‖G.normalTrace‖ * ‖q‖ * ‖v‖ := by
  calc
    ‖G.normalTrace q v‖ ≤ ‖G.normalTrace q‖ * ‖v‖ :=
      ContinuousLinearMap.le_opNorm (G.normalTrace q) v
    _ ≤ (‖G.normalTrace‖ * ‖q‖) * ‖v‖ := by
      exact mul_le_mul_of_nonneg_right
        (ContinuousLinearMap.le_opNorm G.normalTrace q) (norm_nonneg v)
    _ = ‖G.normalTrace‖ * ‖q‖ * ‖v‖ := rfl

/--
Two bounded normal-trace extensions that agree on dense cores are identical.
This is the uniqueness half of the graph-space extension argument.
-/
theorem normalTrace_unique_of_dense_agreement
    {V Q : Type*}
    [NormedAddCommGroup V] [NormedSpace ℝ V]
    [NormedAddCommGroup Q] [NormedSpace ℝ Q]
    (G H : BoundedGreenPairing V Q)
    (Q0 : Submodule ℝ Q) (V0 : Submodule ℝ V)
    (hQ : Dense (Q0 : Set Q)) (hV : Dense (V0 : Set V))
    (hagree : ∀ q, q ∈ Q0 → ∀ v, v ∈ V0 →
      G.normalTrace q v = H.normalTrace q v) :
    G.normalTrace = H.normalTrace := by
  apply ContinuousLinearMap.ext_on (s := (Q0 : Set Q)) (by simpa using hQ)
  intro q hq
  apply ContinuousLinearMap.ext_on (s := (V0 : Set V)) (by simpa using hV)
  intro v hv
  exact hagree q hq v hv

/--
Smooth cores together with the two density statements needed to extend classical
Green's formula to the graph-space completion.
-/
structure GreenSmoothCore
    {V Q : Type*}
    [NormedAddCommGroup V] [NormedSpace ℝ V]
    [NormedAddCommGroup Q] [NormedSpace ℝ Q]
    (G : BoundedGreenPairing V Q) where
  smoothV : Submodule ℝ V
  smoothQ : Submodule ℝ Q
  denseV : Dense (smoothV : Set V)
  denseQ : Dense (smoothQ : Set Q)
  smoothGreen : ∀ q, q ∈ smoothQ → ∀ v, v ∈ smoothV →
    G.normalTrace q v = G.volumePairing q v

/--
Density plus continuity extends the smooth Green identity to all graph-space fields.
No boundary value is postulated here: the extension is forced by the continuous maps.
-/
theorem weakGreen_of_denseSmoothCore
    {V Q : Type*}
    [NormedAddCommGroup V] [NormedSpace ℝ V]
    [NormedAddCommGroup Q] [NormedSpace ℝ Q]
    (G : BoundedGreenPairing V Q) (C : GreenSmoothCore G)
    (q : Q) (v : V) :
    G.normalTrace q v = G.volumePairing q v := by
  have houter : G.normalTrace = G.volumePairing := by
    apply ContinuousLinearMap.ext_on (s := (C.smoothQ : Set Q)) (by simpa using C.denseQ)
    intro q hq
    apply ContinuousLinearMap.ext_on (s := (C.smoothV : Set V)) (by simpa using C.denseV)
    intro v hv
    exact C.smoothGreen q hq v hv
  rw [houter]

/-- A test field has zero boundary trace when every normal-trace functional annihilates it. -/
def HasZeroBoundaryTrace
    {V Q : Type*}
    [NormedAddCommGroup V] [NormedSpace ℝ V]
    [NormedAddCommGroup Q] [NormedSpace ℝ Q]
    (G : BoundedGreenPairing V Q) (v : V) : Prop :=
  ∀ q : Q, G.normalTrace q v = 0

/-- The zero test field has zero boundary trace for every bounded Green pairing. -/
@[simp]
theorem hasZeroBoundaryTrace_zero
    {V Q : Type*}
    [NormedAddCommGroup V] [NormedSpace ℝ V]
    [NormedAddCommGroup Q] [NormedSpace ℝ Q]
    (G : BoundedGreenPairing V Q) :
    HasZeroBoundaryTrace G (0 : V) := by
  simp [HasZeroBoundaryTrace]

/-- Zero-boundary test fields form a linear subspace. -/
def zeroBoundarySubmodule
    {V Q : Type*}
    [NormedAddCommGroup V] [NormedSpace ℝ V]
    [NormedAddCommGroup Q] [NormedSpace ℝ Q]
    (G : BoundedGreenPairing V Q) : Submodule ℝ V where
  carrier := {v | HasZeroBoundaryTrace G v}
  zero_mem' := by
    intro q
    simp [HasZeroBoundaryTrace]
  add_mem' := by
    intro v w hv hw q
    simp [map_add, hv q, hw q]
  smul_mem' := by
    intro c v hv q
    simp [map_smul, hv q]

/-- Membership in the zero-boundary submodule is exactly functional trace annihilation. -/
theorem mem_zeroBoundarySubmodule_iff
    {V Q : Type*}
    [NormedAddCommGroup V] [NormedSpace ℝ V]
    [NormedAddCommGroup Q] [NormedSpace ℝ Q]
    (G : BoundedGreenPairing V Q) (v : V) :
    v ∈ zeroBoundarySubmodule G ↔ HasZeroBoundaryTrace G v :=
  Iff.rfl

/-- Weak Green immediately kills the volume pairing against a zero-trace test field. -/
theorem volumePairing_eq_zero_of_zeroBoundaryTrace
    {V Q : Type*}
    [NormedAddCommGroup V] [NormedSpace ℝ V]
    [NormedAddCommGroup Q] [NormedSpace ℝ Q]
    (G : BoundedGreenPairing V Q) (C : GreenSmoothCore G)
    (q : Q) (v : V) (hv : HasZeroBoundaryTrace G v) :
    G.volumePairing q v = 0 := by
  rw [← weakGreen_of_denseSmoothCore G C q v]
  exact hv q

end Continuum

end CACEFormal
