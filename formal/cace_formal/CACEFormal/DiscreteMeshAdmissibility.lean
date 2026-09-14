import CACEFormal.MeshCombinatorics
import CACEFormal.DiscretePragerSynge

namespace CACEFormal

/-- Source-level API for the missing bridge. A future theorem replaces the explicit
orthogonality hypothesis by elementwise Green identities, interior-facet cancellation,
and exact cell equilibrium certificates. -/
theorem discrete_prager_synge_from_mesh_bridge
    {E : Type*} [SeminormedAddCommGroup E] [InnerProductSpace ℝ E]
    (eGrad eFlux : E)
    (meshOrthogonality : inner ℝ eGrad eFlux = 0) :
    ‖eGrad + eFlux‖ * ‖eGrad + eFlux‖ =
      ‖eGrad‖ * ‖eGrad‖ + ‖eFlux‖ * ‖eFlux‖ := by
  exact discrete_prager_synge_of_orthogonality eGrad eFlux meshOrthogonality

end CACEFormal
