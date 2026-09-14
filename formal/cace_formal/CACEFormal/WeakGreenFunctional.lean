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
    apply ContinuousLinearMap.ext_on C.denseQ
    intro q hq
    apply ContinuousLinearMap.ext_on C.denseV
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
