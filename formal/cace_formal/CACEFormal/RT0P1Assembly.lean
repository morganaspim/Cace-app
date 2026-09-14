import Mathlib
import CACEFormal.MeshCertificate
import CACEFormal.DiscreteOrthogonality

namespace CACEFormal

open scoped BigOperators

/--
Generic finite RT0/P1 assembly certificate.

The global discrete Green identity is not stored as an axiom of this object.
Instead, a concrete instance proves an elementwise Green identity and a finite
face-assembly identity.  The theorem below then derives the global Green identity
by summing the local identities and assembling the face terms.

This remains a discrete certificate layer.  It does not claim the later continuum
H¹/H(div) normal-trace or density theorem.
-/
structure RT0P1AssemblyCertificate (mesh : MeshCertificate) where
  /-- Exact element contribution representing `∫_K q · ∇v`. -/
  cellPairing : Fin mesh.triangleCount → ℝ
  /-- Exact element contribution representing `-∫_K (div q) v` in the chosen sign convention. -/
  cellDivergence : Fin mesh.triangleCount → ℝ
  /-- Sum of the three oriented local face contributions of each cell. -/
  cellFacePairing : Fin mesh.triangleCount → ℝ
  /-- Assembled physical-boundary contribution, indexed by cells for compatibility with v3.22. -/
  boundaryPairing : Fin mesh.triangleCount → ℝ
  /-- Assembled two-sided contribution of each interior global edge. -/
  interiorFacePairing : Fin mesh.interiorEdgeCount → ℝ

  /-- Elementwise RT0/P1 Green identity. -/
  localGreenIdentity : ∀ K,
    cellPairing K = cellDivergence K + cellFacePairing K

  /--
  Finite assembly certificate: summing all local face terms is exactly the sum of
  physical-boundary terms plus paired interior-edge terms.
  -/
  faceAssembly :
    (∑ K, cellFacePairing K) =
      (∑ K, boundaryPairing K) +
      (∑ F, interiorFacePairing F)

  equilibrium : ∀ K, cellDivergence K = 0
  boundaryAdmissible : ∀ K, boundaryPairing K = 0
  interiorCancellation : ∀ F, interiorFacePairing F = 0

namespace RT0P1AssemblyCertificate

/--
The global discrete Green identity derived from elementwise Green identities and
finite face assembly.
-/
theorem global_green_identity {mesh : MeshCertificate}
    (cert : RT0P1AssemblyCertificate mesh) :
    (∑ K, cert.cellPairing K) =
      (∑ K, cert.cellDivergence K) +
      (∑ K, cert.boundaryPairing K) +
      (∑ F, cert.interiorFacePairing F) := by
  calc
    (∑ K, cert.cellPairing K) =
        ∑ K, (cert.cellDivergence K + cert.cellFacePairing K) := by
      apply Finset.sum_congr rfl
      intro K _hK
      exact cert.localGreenIdentity K
    _ = (∑ K, cert.cellDivergence K) + (∑ K, cert.cellFacePairing K) := by
      rw [Finset.sum_add_distrib]
    _ = (∑ K, cert.cellDivergence K) +
        (∑ K, cert.boundaryPairing K) +
        (∑ F, cert.interiorFacePairing F) := by
      rw [cert.faceAssembly]
      ring

/-- Every complete RT0/P1 assembly certificate yields exact discrete orthogonality. -/
theorem orthogonality {mesh : MeshCertificate}
    (cert : RT0P1AssemblyCertificate mesh) :
    (∑ K, cert.cellPairing K) = 0 := by
  exact mesh_admissibility_to_orthogonality
    cert.cellPairing
    cert.cellDivergence
    cert.boundaryPairing
    cert.interiorFacePairing
    (global_green_identity cert)
    cert.equilibrium
    cert.boundaryAdmissible
    cert.interiorCancellation

end RT0P1AssemblyCertificate

/--
Generic discrete Prager--Synge endpoint driven by a certified mesh and certified
RT0/P1 assembly. Geometry-specific work is isolated in `MeshCertificate` and the
local/face assembly obligations rather than assumed directly as global
orthogonality.
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
    (RT0P1AssemblyCertificate.global_green_identity cert)
    cert.equilibrium
    cert.boundaryAdmissible
    cert.interiorCancellation

end CACEFormal
