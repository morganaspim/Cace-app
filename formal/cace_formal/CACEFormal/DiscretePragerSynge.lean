import CACEFormal.AbstractPragerSynge

namespace CACEFormal

/-- Discrete hypercircle theorem after a certified finite-mesh bridge produces orthogonality. -/
theorem discrete_prager_synge_of_orthogonality
    {E : Type*} [SeminormedAddCommGroup E] [InnerProductSpace ℝ E]
    (eGrad eFlux : E)
    (horth : inner ℝ eGrad eFlux = 0) :
    ‖eGrad + eFlux‖ * ‖eGrad + eFlux‖ =
      ‖eGrad‖ * ‖eGrad‖ + ‖eFlux‖ * ‖eFlux‖ := by
  exact abstract_prager_synge eGrad eFlux horth

end CACEFormal
