import Mathlib
import CACEFormal.Hypercircle
import CACEFormal.MeshCertificate
import CACEFormal.MeshFaceAssembly
import CACEFormal.P1RT0Element

namespace CACEFormal

open scoped BigOperators

/-!
Strengthened v3.24 assembly API.

Compared with `RT0P1AssemblyCertificate`, this certificate stores local face
contributions rather than an independent global `faceAssembly` equality.  The
global face partition is proved from `MeshCertificate` in `MeshFaceAssembly`.
-/

structure RT0P1DerivedAssemblyCertificate (mesh : MeshCertificate) where
  cellPairing : Fin mesh.triangleCount → ℝ
  cellDivergence : Fin mesh.triangleCount → ℝ
  localFacePairing : Fin mesh.triangleCount → Fin 3 → ℝ
  localGreenIdentity : ∀ K,
    cellPairing K = cellDivergence K + ∑ s, localFacePairing K s
  equilibrium : ∀ K, cellDivergence K = 0
  boundaryAdmissible : ∀ b,
    localFacePairing (mesh.boundaryCell b) (mesh.boundarySlot b) = 0
  interiorCancellation : ∀ i,
    localFacePairing (mesh.interiorLeftCell i) (mesh.interiorLeftSlot i) +
      localFacePairing (mesh.interiorRightCell i) (mesh.interiorRightSlot i) = 0

namespace RT0P1DerivedAssemblyCertificate

/-- Global Green assembly now follows from local Green plus certified mesh ownership. -/
theorem global_green_identity {mesh : MeshCertificate}
    (cert : RT0P1DerivedAssemblyCertificate mesh) :
    (∑ K, cert.cellPairing K) =
      (∑ K, cert.cellDivergence K) +
      (∑ i, cert.localFacePairing (mesh.interiorLeftCell i) (mesh.interiorLeftSlot i) +
        cert.localFacePairing (mesh.interiorRightCell i) (mesh.interiorRightSlot i)) +
      (∑ b, cert.localFacePairing (mesh.boundaryCell b) (mesh.boundarySlot b)) := by
  calc
    (∑ K, cert.cellPairing K) =
        ∑ K, (cert.cellDivergence K + ∑ s, cert.localFacePairing K s) := by
      apply Finset.sum_congr rfl
      intro K _
      exact cert.localGreenIdentity K
    _ = (∑ K, cert.cellDivergence K) + (∑ K, ∑ s, cert.localFacePairing K s) := by
      rw [Finset.sum_add_distrib]
    _ = (∑ K, cert.cellDivergence K) +
        ((∑ i, cert.localFacePairing (mesh.interiorLeftCell i) (mesh.interiorLeftSlot i) +
          cert.localFacePairing (mesh.interiorRightCell i) (mesh.interiorRightSlot i)) +
        (∑ b, cert.localFacePairing (mesh.boundaryCell b) (mesh.boundarySlot b))) := by
      rw [local_face_sum_decomposition mesh cert.localFacePairing]
    _ = _ := by ring

/-- Equilibrium, boundary admissibility and interior cancellation imply orthogonality. -/
theorem orthogonality {mesh : MeshCertificate}
    (cert : RT0P1DerivedAssemblyCertificate mesh) :
    (∑ K, cert.cellPairing K) = 0 := by
  rw [cert.global_green_identity]
  have hdiv : (∑ K, cert.cellDivergence K) = 0 := by
    apply Finset.sum_eq_zero
    intro K _
    exact cert.equilibrium K
  have hint :
      (∑ i, cert.localFacePairing (mesh.interiorLeftCell i) (mesh.interiorLeftSlot i) +
        cert.localFacePairing (mesh.interiorRightCell i) (mesh.interiorRightSlot i)) = 0 := by
    apply Finset.sum_eq_zero
    intro i _
    exact cert.interiorCancellation i
  have hbdy :
      (∑ b, cert.localFacePairing (mesh.boundaryCell b) (mesh.boundarySlot b)) = 0 := by
    apply Finset.sum_eq_zero
    intro b _
    exact cert.boundaryAdmissible b
  rw [hdiv, hint, hbdy]
  norm_num

/--
Build the strengthened assembly certificate from actual affine P1 and RT0
element data.  The local Green identity is derived automatically from
`P1RT0Element.local_green_identity`; callers only prove physical admissibility
conditions (equilibrium and face cancellation).
-/
def ofExactElements {mesh : MeshCertificate}
    (triangle : Fin mesh.triangleCount → Triangle2)
    (primal : Fin mesh.triangleCount → P1Affine)
    (flux : Fin mesh.triangleCount → RT0Affine)
    (hEquilibrium : ∀ K,
      P1RT0Element.cellDivergence (triangle K) (primal K) (flux K) = 0)
    (hBoundary : ∀ b,
      P1RT0Element.localFacePairing
        (triangle (mesh.boundaryCell b))
        (primal (mesh.boundaryCell b))
        (flux (mesh.boundaryCell b))
        (mesh.boundarySlot b) = 0)
    (hInterior : ∀ i,
      P1RT0Element.localFacePairing
          (triangle (mesh.interiorLeftCell i))
          (primal (mesh.interiorLeftCell i))
          (flux (mesh.interiorLeftCell i))
          (mesh.interiorLeftSlot i) +
        P1RT0Element.localFacePairing
          (triangle (mesh.interiorRightCell i))
          (primal (mesh.interiorRightCell i))
          (flux (mesh.interiorRightCell i))
          (mesh.interiorRightSlot i) = 0) :
    RT0P1DerivedAssemblyCertificate mesh where
  cellPairing := fun K => P1RT0Element.cellPairing (triangle K) (primal K) (flux K)
  cellDivergence := fun K => P1RT0Element.cellDivergence (triangle K) (primal K) (flux K)
  localFacePairing := fun K s =>
    P1RT0Element.localFacePairing (triangle K) (primal K) (flux K) s
  localGreenIdentity := by
    intro K
    calc
      P1RT0Element.cellPairing (triangle K) (primal K) (flux K) =
          P1RT0Element.cellDivergence (triangle K) (primal K) (flux K) +
            P1RT0Element.cellFacePairing (triangle K) (primal K) (flux K) :=
        P1RT0Element.local_green_identity (triangle K) (primal K) (flux K)
      _ = P1RT0Element.cellDivergence (triangle K) (primal K) (flux K) +
          ∑ s, P1RT0Element.localFacePairing (triangle K) (primal K) (flux K) s := by
        rw [P1RT0Element.sum_localFacePairing]
  equilibrium := hEquilibrium
  boundaryAdmissible := hBoundary
  interiorCancellation := hInterior

end RT0P1DerivedAssemblyCertificate

/-- Derived-assembly Prager--Synge endpoint. -/
theorem discrete_prager_synge_of_derived_rt0_p1_assembly
    {mesh : MeshCertificate}
    (cert : RT0P1DerivedAssemblyCertificate mesh)
    {E : Type*} [SeminormedAddCommGroup E] [InnerProductSpace ℝ E]
    (eGrad eFlux : E)
    (hInner : inner ℝ eGrad eFlux = ∑ K, cert.cellPairing K) :
    ‖eGrad + eFlux‖ * ‖eGrad + eFlux‖ =
      ‖eGrad‖ * ‖eGrad‖ + ‖eFlux‖ * ‖eFlux‖ := by
  apply hypercircle_of_inner_eq_zero
  calc
    inner ℝ eGrad eFlux = ∑ K, cert.cellPairing K := hInner
    _ = 0 := cert.orthogonality

end CACEFormal
