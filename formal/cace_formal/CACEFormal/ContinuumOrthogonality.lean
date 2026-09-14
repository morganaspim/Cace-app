import CACEFormal.WeakGreenFunctional

namespace CACEFormal

namespace Continuum

/--
Zero-boundary weak Green orthogonality.  The PDE layer only has to identify its
cross term with the volume Green pairing; density and boundary cancellation are
then handled by `weakGreen_of_denseSmoothCore`.
-/
theorem zeroBoundaryOrthogonality
    {V Q E : Type*}
    [NormedAddCommGroup V] [NormedSpace ℝ V]
    [NormedAddCommGroup Q] [NormedSpace ℝ Q]
    [SeminormedAddCommGroup E] [InnerProductSpace ℝ E]
    (G : BoundedGreenPairing V Q) (C : GreenSmoothCore G)
    (q : Q) (v : V) (hv : HasZeroBoundaryTrace G v)
    (eGrad eFlux : E)
    (hcross : inner ℝ eGrad eFlux = G.volumePairing q v) :
    inner ℝ eGrad eFlux = 0 := by
  rw [hcross]
  exact volumePairing_eq_zero_of_zeroBoundaryTrace G C q v hv

end Continuum

end CACEFormal
