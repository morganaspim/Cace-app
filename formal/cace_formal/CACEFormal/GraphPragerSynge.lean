import CACEFormal.GraphGreenPairing
import CACEFormal.ContinuumPragerSynge

namespace CACEFormal

namespace Continuum

/-- Zero-boundary orthogonality specialized to the closed H¹/H(div) graph spaces. -/
theorem graphZeroBoundaryOrthogonality
    {E : Type*} [SeminormedAddCommGroup E] [InnerProductSpace ℝ E]
    (n : Nat)
    (q : HDivGraphClosedSpace n) (v : H1GraphClosedSpace n)
    (hv : HasZeroBoundaryTrace (graphBoundedGreenPairing n) v)
    (eGrad eFlux : E)
    (hcross : inner ℝ eGrad eFlux = closedGraphGreenPairing n q v) :
    inner ℝ eGrad eFlux = 0 := by
  exact zeroBoundaryOrthogonality
    (graphBoundedGreenPairing n) (graphGreenSmoothCore n)
    q v hv eGrad eFlux hcross

/--
Continuum Prager–Synge identity specialized to the closed graph-space model.
The PDE-specific remaining input is the identification of its cross term with the
closed Green pairing and the zero-boundary condition for the primal error.
-/
theorem graphContinuumPragerSynge
    {E : Type*} [SeminormedAddCommGroup E] [InnerProductSpace ℝ E]
    (n : Nat)
    (q : HDivGraphClosedSpace n) (v : H1GraphClosedSpace n)
    (hv : HasZeroBoundaryTrace (graphBoundedGreenPairing n) v)
    (eGrad eFlux : E)
    (hcross : inner ℝ eGrad eFlux = closedGraphGreenPairing n q v) :
    ‖eGrad + eFlux‖ * ‖eGrad + eFlux‖ =
      ‖eGrad‖ * ‖eGrad‖ + ‖eFlux‖ * ‖eFlux‖ := by
  exact continuumPragerSynge_of_weakGreen
    (graphBoundedGreenPairing n) (graphGreenSmoothCore n)
    q v hv eGrad eFlux hcross

end Continuum

end CACEFormal
