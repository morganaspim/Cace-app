import Mathlib
import CACEFormal.RT0P1Assembly
import CACEFormal.ConcreteMeshCertificate
import CACEFormal.Generated.V323MeshCertificate

namespace CACEFormal.Generated

open CACEFormal
open scoped BigOperators

/--
The already verified v3.22 exact rational fixture, routed through the generic
v3.23 geometry-linked mesh certificate and the v3.24 local-to-global RT0/P1
assembly certificate API.
-/
def v324SquareCenterAssembly : RT0P1AssemblyCertificate v323SquareCenterMesh where
  cellPairing := v322CellPairing
  cellDivergence := v322CellDivergence
  cellFacePairing := v322CellPairing
  boundaryPairing := v322BoundaryPairing
  interiorFacePairing := v322InteriorFacePairing
  localGreenIdentity := by
    intro K
    simp [v322CellDivergence, v322FluxError]
  faceAssembly := by
    rw [v322_global_green_identity]
    simp [v322CellDivergence, v322FluxError]
  equilibrium := v322_divergence_free
  boundaryAdmissible := v322_boundary_terms_zero
  interiorCancellation := v322_interior_faces_cancel

/-- The v3.24 global Green identity is now derived from local identities + face assembly. -/
theorem v324_square_center_global_green_identity :
    (∑ K, v324SquareCenterAssembly.cellPairing K) =
      (∑ K, v324SquareCenterAssembly.cellDivergence K) +
      (∑ K, v324SquareCenterAssembly.boundaryPairing K) +
      (∑ F, v324SquareCenterAssembly.interiorFacePairing F) := by
  exact RT0P1AssemblyCertificate.global_green_identity v324SquareCenterAssembly

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
