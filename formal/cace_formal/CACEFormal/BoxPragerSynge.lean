import CACEFormal.BoxGraphGreenPairing
import CACEFormal.ContinuumPragerSynge
import CACEFormal.WeightedEnergy

namespace CACEFormal

namespace Continuum

/-!
# Concrete bounded-box Prager--Synge endpoints

The generic continuum theorem is now instantiated directly on CACE's
restricted-measure box graph closures and their already-proved dense smooth
Green core.  Callers no longer need to manually package the bounded Green
pairing or density witnesses.
-/

/-- Concrete Prager--Synge theorem on the CACE bounded-box graph spaces. -/
theorem boxGraphPragerSynge
    {n : Nat} (a b : BoxPoint n)
    (q : BoxHDivGraphClosedSpace a b)
    (v : BoxH1GraphClosedSpace a b)
    (hv : HasZeroBoundaryTrace (boxGraphBoundedGreenPairing a b) v)
    {E : Type*} [SeminormedAddCommGroup E] [InnerProductSpace ℝ E]
    (eGrad eFlux : E)
    (hcross : inner ℝ eGrad eFlux =
      (boxGraphBoundedGreenPairing a b).volumePairing q v) :
    ‖eGrad + eFlux‖ * ‖eGrad + eFlux‖ =
      ‖eGrad‖ * ‖eGrad‖ + ‖eFlux‖ * ‖eFlux‖ := by
  exact continuumPragerSynge_of_weakGreen
    (boxGraphBoundedGreenPairing a b)
    (boxGraphGreenSmoothCore a b)
    q v hv eGrad eFlux hcross

/-- Submodule-membership form of the concrete box endpoint. -/
theorem boxGraphPragerSynge_of_mem_zeroBoundary
    {n : Nat} (a b : BoxPoint n)
    (q : BoxHDivGraphClosedSpace a b)
    (v : BoxH1GraphClosedSpace a b)
    (hv : v ∈ zeroBoundarySubmodule (boxGraphBoundedGreenPairing a b))
    {E : Type*} [SeminormedAddCommGroup E] [InnerProductSpace ℝ E]
    (eGrad eFlux : E)
    (hcross : inner ℝ eGrad eFlux =
      (boxGraphBoundedGreenPairing a b).volumePairing q v) :
    ‖eGrad + eFlux‖ * ‖eGrad + eFlux‖ =
      ‖eGrad‖ * ‖eGrad‖ + ‖eFlux‖ * ‖eFlux‖ := by
  apply boxGraphPragerSynge a b q v
  · exact (mem_zeroBoundarySubmodule_iff
      (boxGraphBoundedGreenPairing a b) v).mp hv
  · exact hcross

/-- Weighted-energy bounded-box endpoint.

The same box weak-Green proof annihilates the weighted error cross term, after
which the certified SPD energy operator supplies the weighted hypercircle
identity.
-/
theorem boxGraphWeightedHypercircle
    {n : Nat} (a b : BoxPoint n)
    (q : BoxHDivGraphClosedSpace a b)
    (v : BoxH1GraphClosedSpace a b)
    (hv : HasZeroBoundaryTrace (boxGraphBoundedGreenPairing a b) v)
    {E : Type*} [NormedAddCommGroup E] [InnerProductSpace ℝ E]
    (A : SPDEnergyOperator E)
    (eGrad eFlux : E)
    (hcross : inner ℝ (A.op eGrad) eFlux =
      (boxGraphBoundedGreenPairing a b).volumePairing q v) :
    A.energySq (eGrad + eFlux) =
      A.energySq eGrad + A.energySq eFlux := by
  have hvolume :
      (boxGraphBoundedGreenPairing a b).volumePairing q v = 0 :=
    volumePairing_eq_zero_of_zeroBoundaryTrace
      (boxGraphBoundedGreenPairing a b)
      (boxGraphGreenSmoothCore a b)
      q v hv
  have horth : inner ℝ (A.op eGrad) eFlux = 0 := by
    rw [hcross, hvolume]
  exact A.weighted_hypercircle eGrad eFlux horth

end Continuum

end CACEFormal
