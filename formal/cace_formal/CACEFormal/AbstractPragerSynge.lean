import CACEFormal.Hypercircle

namespace CACEFormal

/-- Abstract Prager–Synge algebra once the PDE layer supplies orthogonality. -/
theorem abstract_prager_synge
    {E : Type*} [SeminormedAddCommGroup E] [InnerProductSpace ℝ E]
    (eGrad eFlux : E)
    (horth : inner ℝ eGrad eFlux = 0) :
    ‖eGrad + eFlux‖ * ‖eGrad + eFlux‖ =
      ‖eGrad‖ * ‖eGrad‖ + ‖eFlux‖ * ‖eFlux‖ := by
  exact hypercircle_of_inner_eq_zero horth

end CACEFormal
