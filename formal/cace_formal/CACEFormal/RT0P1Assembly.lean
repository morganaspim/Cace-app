import Mathlib
import CACEFormal.MeshCertificate
import CACEFormal.DiscreteOrthogonality

namespace CACEFormal

open scoped BigOperators

/--
Generic finite RT0/P1 assembly certificate.

This is a discrete certificate layer: the mesh is general, but each concrete
instantiation must still prove its exact elementwise/assembled Green identity,
equilibrium, boundary admissibility, and interior-edge cancellation.  It does not
claim the later continuum H¹/H(div) trace theorem.
-/
structure RT0P1AssemblyCertificate (mesh : MeshCertificate) where
  cellPairing : Fin mesh.triangleCount → ℝ
  cellDivergence : Fin mesh.triangleCount → ℝ
  boundaryPairing : Fin mesh.triangleCount → ℝ
  interiorFacePairing : Fin mesh.interiorEdgeCount → ℝ

  greenIdentity :
    (∑ K, cellPairing K) =
      (∑ K, cellDivergence K) +
      (∑ K, boundaryPairing K) +
      (∑ F, interiorFacePairing F)
  equilibrium : ∀ K, cellDivergence K = 0
  boundaryAdmissible : ∀ K, boundaryPairing K = 0
  interiorCancellation : ∀ F, interiorFacePairing F = 0

namespace RT0P1AssemblyCertificate

/-- The certified global discrete Green identity. -/
theorem global_green_identity {mesh : MeshCertificate}
    (cert : RT0P1AssemblyCertificate mesh) :
    (∑ K, cert.cellPairing K) =
      (∑ K, cert.cellDivergence K) +
      (∑ K, cert.boundaryPairing K) +
      (∑ F, cert.interiorFacePairing F) :=
  cert.greenIdentity

/-- Every complete RT0/P1 assembly certificate yields exact discrete orthogonality. -/
theorem orthogonality {mesh : MeshCertificate}
    (cert : RT0P1AssemblyCertificate mesh) :
    (∑ K, cert.cellPairing K) = 0 := by
  exact mesh_admissibility_to_orthogonality
    cert.cellPairing
    cert.cellDivergence
    cert.boundaryPairing
    cert.interiorFacePairing
    cert.greenIdentity
    cert.equilibrium
    cert.boundaryAdmissible
    cert.interiorCancellation

end RT0P1AssemblyCertificate

/--
Generic discrete Prager--Synge endpoint driven by a certified mesh and certified
RT0/P1 assembly.  Geometry-specific work is isolated in `MeshCertificate` and
`RT0P1AssemblyCertificate` rather than assumed directly as orthogonality.
-/
theorem discrete_prager_synge_of_rt0_p1_assembly
    {E : Type*} [SeminormedAddCommGroup E] [InnerProductSpace ℝ E]
    {mesh : MeshCertificate}
    (cert : RT0P1AssemblyCertificate mesh)
    (eGrad eFlux : E)
    (hInner : inner ℝ eGrad eFlux = ∑ K, cert.cellPairing K) :
    ‖eGrad + eFlux‖ * ‖eGrad + eFlux‖ =
      ‖eGrad‖ * ‖eGrad‖ + ‖eFlux‖ * ‖eFlux‖ := by
  exact discrete_prager_synge_from_mesh_admissibility
    eGrad
    eFlux
    cert.cellPairing
    cert.cellDivergence
    cert.boundaryPairing
    cert.interiorFacePairing
    hInner
    cert.greenIdentity
    cert.equilibrium
    cert.boundaryAdmissible
    cert.interiorCancellation

end CACEFormal
