import CACEFormal.BoxGraphTrace
import CACEFormal.GraphGreenPairing

namespace CACEFormal

open Set Finset MeasureTheory
open scoped BigOperators InnerProductSpace

namespace Continuum

noncomputable section

/-!
# Continuous Green pairing on bounded-box graph closures

This is the bounded-domain analogue of `GraphGreenPairing`.  The ambient graph coordinates use
`L²` for the restricted box measure, so the pairing is a genuinely bounded-domain volume pairing.
The trace is first defined functionally by this continuous Green pairing.  A later theorem identifies
its values on the dense smooth core with the classical signed face-flux trace.
-/

/-- Coordinate projection from box H(div) graph data. -/
noncomputable def boxHDivFieldProj {n : Nat} (a b : BoxPoint n) (i : Fin (n + 1)) :
    BoxHDivGraphAmbient a b →L[ℝ] BoxL2 a b :=
  (ContinuousLinearMap.proj i).comp
    (ContinuousLinearMap.fst ℝ (Fin (n + 1) → BoxL2 a b) (BoxL2 a b))

/-- Divergence-coordinate projection from box H(div) graph data. -/
noncomputable def boxHDivDivProj {n : Nat} (a b : BoxPoint n) :
    BoxHDivGraphAmbient a b →L[ℝ] BoxL2 a b :=
  ContinuousLinearMap.snd ℝ (Fin (n + 1) → BoxL2 a b) (BoxL2 a b)

/-- Value projection from box H¹ graph data. -/
noncomputable def boxH1ValueProj {n : Nat} (a b : BoxPoint n) :
    BoxH1GraphAmbient a b →L[ℝ] BoxL2 a b :=
  ContinuousLinearMap.fst ℝ (BoxL2 a b) (Fin (n + 1) → BoxL2 a b)

/-- Gradient-coordinate projection from box H¹ graph data. -/
noncomputable def boxH1GradProj {n : Nat} (a b : BoxPoint n) (i : Fin (n + 1)) :
    BoxH1GraphAmbient a b →L[ℝ] BoxL2 a b :=
  (ContinuousLinearMap.proj i).comp
    (ContinuousLinearMap.snd ℝ (BoxL2 a b) (Fin (n + 1) → BoxL2 a b))

/--
Bounded-box Green volume pairing
`(q,v) ↦ Σᵢ ⟪qᵢ, ∂ᵢv⟫ + ⟪div q, v⟫`
on the ambient restricted-measure graph coordinates.
-/
noncomputable def ambientBoxGraphGreenPairing {n : Nat} (a b : BoxPoint n) :
    BoxHDivGraphAmbient a b →L[ℝ] BoxH1GraphAmbient a b →L[ℝ] ℝ :=
  (∑ i : Fin (n + 1),
      innerThrough (boxHDivFieldProj a b i) (boxH1GradProj a b i)) +
    innerThrough (boxHDivDivProj a b) (boxH1ValueProj a b)

/-- Coordinate formula for the bounded-box Green pairing. -/
theorem ambientBoxGraphGreenPairing_apply {n : Nat} (a b : BoxPoint n)
    (q : BoxHDivGraphAmbient a b) (v : BoxH1GraphAmbient a b) :
    ambientBoxGraphGreenPairing a b q v =
      (∑ i : Fin (n + 1), inner ℝ (q.1 i) (v.2 i)) + inner ℝ q.2 v.1 := by
  simp [ambientBoxGraphGreenPairing, innerThrough, boxHDivFieldProj,
    boxHDivDivProj, boxH1ValueProj, boxH1GradProj]

/-- Restrict the bounded-box Green pairing to the closed graph spaces. -/
noncomputable def closedBoxGraphGreenPairing {n : Nat} (a b : BoxPoint n) :
    BoxHDivGraphClosedSpace a b →L[ℝ] BoxH1GraphClosedSpace a b →L[ℝ] ℝ :=
  let qIncl : BoxHDivGraphClosedSpace a b →L[ℝ] BoxHDivGraphAmbient a b :=
    Submodule.subtypeL ((BoxHDivSmoothGraphCore a b).topologicalClosure)
  let vIncl : BoxH1GraphClosedSpace a b →L[ℝ] BoxH1GraphAmbient a b :=
    Submodule.subtypeL ((BoxH1SmoothGraphCore a b).topologicalClosure)
  (ContinuousLinearMap.precomp ℝ vIncl).comp
    ((ambientBoxGraphGreenPairing a b).comp qIncl)

/-- Coordinate formula for the bounded-box Green pairing after restriction to the closed graph spaces. -/
theorem closedBoxGraphGreenPairing_apply {n : Nat} (a b : BoxPoint n)
    (q : BoxHDivGraphClosedSpace a b) (v : BoxH1GraphClosedSpace a b) :
    closedBoxGraphGreenPairing a b q v =
      (∑ i : Fin (n + 1), inner ℝ (q.1.1 i) (v.1.2 i)) +
        inner ℝ q.1.2 v.1.1 := by
  change ambientBoxGraphGreenPairing a b q.1 v.1 = _
  exact ambientBoxGraphGreenPairing_apply a b q.1 v.1

/-- Functional bounded-box normal trace on the graph closure. -/
noncomputable def boxGraphNormalTrace {n : Nat} (a b : BoxPoint n) :
    BoxHDivGraphClosedSpace a b →L[ℝ] BoxH1GraphClosedSpace a b →L[ℝ] ℝ :=
  closedBoxGraphGreenPairing a b

/-- Bounded Green-pairing package for the box graph closures. -/
noncomputable def boxGraphBoundedGreenPairing {n : Nat} (a b : BoxPoint n) :
    BoundedGreenPairing (BoxH1GraphClosedSpace a b) (BoxHDivGraphClosedSpace a b) where
  volumePairing := closedBoxGraphGreenPairing a b
  normalTrace := boxGraphNormalTrace a b

/-- The dense box smooth cores form a Green core for the functional trace. -/
noncomputable def boxGraphGreenSmoothCore {n : Nat} (a b : BoxPoint n) :
    GreenSmoothCore (boxGraphBoundedGreenPairing a b) where
  smoothV := BoxH1DenseSmoothCore a b
  smoothQ := BoxHDivDenseSmoothCore a b
  denseV := dense_BoxH1DenseSmoothCore a b
  denseQ := dense_BoxHDivDenseSmoothCore a b
  smoothGreen := by
    intro q hq v hv
    rfl

/-- Weak Green identity on the bounded-box closed graph spaces. -/
theorem boxGraphWeakGreen {n : Nat} (a b : BoxPoint n)
    (q : BoxHDivGraphClosedSpace a b) (v : BoxH1GraphClosedSpace a b) :
    (boxGraphBoundedGreenPairing a b).normalTrace q v =
      (boxGraphBoundedGreenPairing a b).volumePairing q v :=
  weakGreen_of_denseSmoothCore
    (boxGraphBoundedGreenPairing a b) (boxGraphGreenSmoothCore a b) q v

/-- The functional box normal trace is continuous in the H(div) graph variable. -/
theorem boxGraphNormalTrace_continuous {n : Nat} (a b : BoxPoint n) :
    Continuous (boxGraphNormalTrace a b) :=
  (boxGraphNormalTrace a b).continuous

end

end Continuum

end CACEFormal
