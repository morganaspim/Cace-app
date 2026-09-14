import CACEFormal.GraphClosedSpaces
import CACEFormal.WeakGreenFunctional
import Mathlib.Analysis.InnerProductSpace.LinearMap
import Mathlib.Analysis.Normed.Operator.Basic
import Mathlib.Topology.Algebra.Module.ContinuousLinearMap.Restrict
import Mathlib.Topology.Algebra.Module.Spaces.ContinuousLinearMap

namespace CACEFormal

open scoped BigOperators

namespace Continuum

/-- Pair an `A`-projection and a `B`-projection through the real Hilbert inner product. -/
noncomputable def innerThrough
    {A B H : Type*}
    [NormedAddCommGroup A] [NormedSpace ℝ A]
    [NormedAddCommGroup B] [NormedSpace ℝ B]
    [NormedAddCommGroup H] [InnerProductSpace ℝ H]
    (p : A →L[ℝ] H) (q : B →L[ℝ] H) :
    A →L[ℝ] B →L[ℝ] ℝ :=
  (ContinuousLinearMap.precomp ℝ q).comp ((innerSL ℝ).comp p)

/-- Vector-component projection from H(div) graph data. -/
noncomputable def hdivFieldProj (n : Nat) (i : Fin n) :
    HDivGraphAmbient n →L[ℝ] RealL2 n :=
  (ContinuousLinearMap.proj i).comp
    (ContinuousLinearMap.fst ℝ (Fin n → RealL2 n) (RealL2 n))

/-- Divergence projection from H(div) graph data. -/
noncomputable def hdivDivProj (n : Nat) :
    HDivGraphAmbient n →L[ℝ] RealL2 n :=
  ContinuousLinearMap.snd ℝ (Fin n → RealL2 n) (RealL2 n)

/-- Value projection from H¹ graph data. -/
noncomputable def h1ValueProj (n : Nat) :
    H1GraphAmbient n →L[ℝ] RealL2 n :=
  ContinuousLinearMap.fst ℝ (RealL2 n) (Fin n → RealL2 n)

/-- Gradient-component projection from H¹ graph data. -/
noncomputable def h1GradProj (n : Nat) (i : Fin n) :
    H1GraphAmbient n →L[ℝ] RealL2 n :=
  (ContinuousLinearMap.proj i).comp
    (ContinuousLinearMap.snd ℝ (RealL2 n) (Fin n → RealL2 n))

/--
The graph-space Green volume pairing
`(q,v) ↦ Σᵢ ⟪qᵢ, ∂ᵢv⟫ + ⟪div q, v⟫` on the ambient L² graph data.
Continuity is obtained compositionally from the Hilbert inner product and coordinate projections.
-/
noncomputable def ambientGraphGreenPairing (n : Nat) :
    HDivGraphAmbient n →L[ℝ] H1GraphAmbient n →L[ℝ] ℝ :=
  (∑ i : Fin n, innerThrough (hdivFieldProj n i) (h1GradProj n i)) +
    innerThrough (hdivDivProj n) (h1ValueProj n)

/-- Restrict the ambient continuous Green pairing to the closed smooth graph spaces. -/
noncomputable def closedGraphGreenPairing (n : Nat) :
    HDivGraphClosedSpace n →L[ℝ] H1GraphClosedSpace n →L[ℝ] ℝ :=
  let qIncl : HDivGraphClosedSpace n →L[ℝ] HDivGraphAmbient n :=
    Submodule.subtypeL ((HDivSmoothGraphCore n).topologicalClosure)
  let vIncl : H1GraphClosedSpace n →L[ℝ] H1GraphAmbient n :=
    Submodule.subtypeL ((H1SmoothGraphCore n).topologicalClosure)
  (ContinuousLinearMap.precomp ℝ vIncl).comp
    ((ambientGraphGreenPairing n).comp qIncl)

/--
Functional normal trace on the graph closure.  At this stage it is defined by the bounded
Green volume functional; the separate box theorem identifies this functional with classical
signed face flux on smooth fields.
-/
noncomputable def graphNormalTrace (n : Nat) :
    HDivGraphClosedSpace n →L[ℝ] H1GraphClosedSpace n →L[ℝ] ℝ :=
  closedGraphGreenPairing n

/-- The concrete bounded Green-pairing package on the closed H¹/H(div) graph spaces. -/
noncomputable def graphBoundedGreenPairing (n : Nat) :
    BoundedGreenPairing (H1GraphClosedSpace n) (HDivGraphClosedSpace n) where
  volumePairing := closedGraphGreenPairing n
  normalTrace := graphNormalTrace n

/-- The smooth graph cores form a dense Green core for the functional trace definition. -/
noncomputable def graphGreenSmoothCore (n : Nat) :
    GreenSmoothCore (graphBoundedGreenPairing n) where
  smoothV := H1DenseSmoothCore n
  smoothQ := HDivDenseSmoothCore n
  denseV := dense_H1DenseSmoothCore n
  denseQ := dense_HDivDenseSmoothCore n
  smoothGreen := by
    intro q hq v hv
    rfl

/-- Weak Green identity on the closed graph spaces. -/
theorem graphWeakGreen (n : Nat)
    (q : HDivGraphClosedSpace n) (v : H1GraphClosedSpace n) :
    (graphBoundedGreenPairing n).normalTrace q v =
      (graphBoundedGreenPairing n).volumePairing q v :=
  weakGreen_of_denseSmoothCore
    (graphBoundedGreenPairing n) (graphGreenSmoothCore n) q v

/-- The graph normal trace obeys an explicit operator-norm bound. -/
theorem graphNormalTrace_bound (n : Nat)
    (q : HDivGraphClosedSpace n) (v : H1GraphClosedSpace n) :
    ‖graphNormalTrace n q v‖ ≤
      ‖graphNormalTrace n‖ * ‖q‖ * ‖v‖ :=
  BoundedGreenPairing.normalTrace_bound (graphBoundedGreenPairing n) q v

end Continuum

end CACEFormal
