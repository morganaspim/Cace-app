import Mathlib
import CACEFormal.RT0P1Assembly
import CACEFormal.ConcreteMeshCertificate
import CACEFormal.Generated.V323MeshCertificate

namespace CACEFormal.Generated

open CACEFormal
open scoped BigOperators

/--
The already verified v3.22 exact rational fixture, routed through the generic
v3.23 mesh certificate and v3.24 RT0/P1 assembly certificate APIs.
-/
def v324SquareCenterAssembly : RT0P1AssemblyCertificate v323SquareCenterMesh where
  cellPairing := v322CellPairing
  cellDivergence := v322CellDivergence
  boundaryPairing := v322BoundaryPairing
  interiorFacePairing := v322InteriorFacePairing
  greenIdentity := v322_global_green_identity
  equilibrium := v322_divergence_free
  boundaryAdmissible := v322_boundary_terms_zero
  interiorCancellation := v322_interior_faces_cancel

/-- v3.24 generic assembly recovers exact orthogonality for the fixed v3.22 fixture. -/
theorem v324_square_center_orthogonality :
    (∑ K, v324SquareCenterAssembly.cellPairing K) = 0 := by
  exact RT0P1AssemblyCertificate.orthogonality v324SquareCenterAssembly

/-- v3.24 routes the fixture through the generic assembly-to-Prager--Synge theorem. -/
theorem v324_square_center_prager_synge
    {E : Type*} [SeminormedAddCommGroup E] [InnerProductSpace ℝ E]
    (eGrad eFlux : E)
    (hInner : inner ℝ eGrad eFlux =
      ∑ K, v324SquareCenterAssembly.cellPairing K) :
    ‖eGrad + eFlux‖ * ‖eGrad + eFlux‖ =
      ‖eGrad‖ * ‖eGrad‖ + ‖eFlux‖ * ‖eFlux‖ := by
  exact discrete_prager_synge_of_rt0_p1_assembly
    v324SquareCenterAssembly eGrad eFlux hInner

end CACEFormal.Generated
