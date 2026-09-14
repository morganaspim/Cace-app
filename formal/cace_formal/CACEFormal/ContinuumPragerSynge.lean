import CACEFormal.ContinuumOrthogonality
import CACEFormal.AbstractPragerSynge

namespace CACEFormal

namespace Continuum

/--
Continuum Prager–Synge/hypercircle closure once the PDE cross term has been
identified with a weak Green pairing and the primal error has zero boundary trace.
-/
theorem continuumPragerSynge_of_weakGreen
    {V Q E : Type*}
    [NormedAddCommGroup V] [NormedSpace ℝ V]
    [NormedAddCommGroup Q] [NormedSpace ℝ Q]
    [SeminormedAddCommGroup E] [InnerProductSpace ℝ E]
    (G : BoundedGreenPairing V Q) (C : GreenSmoothCore G)
    (q : Q) (v : V) (hv : HasZeroBoundaryTrace G v)
    (eGrad eFlux : E)
    (hcross : inner ℝ eGrad eFlux = G.volumePairing q v) :
    ‖eGrad + eFlux‖ * ‖eGrad + eFlux‖ =
      ‖eGrad‖ * ‖eGrad‖ + ‖eFlux‖ * ‖eFlux‖ := by
  apply abstract_prager_synge eGrad eFlux
  exact zeroBoundaryOrthogonality G C q v hv eGrad eFlux hcross

end Continuum

end CACEFormal
