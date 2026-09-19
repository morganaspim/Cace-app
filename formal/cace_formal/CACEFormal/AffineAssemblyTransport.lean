import Mathlib
import CACEFormal.AffineP1RT0Transport
import CACEFormal.RT0P1DerivedAssembly

namespace CACEFormal

open scoped BigOperators

/-!
# Affine transport of exact derived RT0/P1 assembly

This module is the next integration layer after `AffineP1RT0Transport`.

A single non-singular affine map is applied to every exact triangle, P1 field,
and RT0 field.  The element and face admissibility hypotheses are transported
by already-proved algebraic invariance theorems, so the strengthened derived
assembly certificate can be rebuilt without adding a new global Green axiom.

This is a useful high-order combination point:

1. affine geometry;
2. Piola/cofactor flux;
3. P1 pullback;
4. exact P1/RT0 element Green algebra;
5. mesh face ownership/assembly;
6. derived assembly;
7. discrete orthogonality;
8. discrete Prager--Synge;
9. hypercircle identity inherited by the endpoint theorem.
-/

namespace AffineAssemblyTransport

open AffineP1RT0Transport

/-- Transport a complete exact-element derived assembly certificate through one
non-singular affine map.  Only the original physical admissibility hypotheses
are required. -/
noncomputable def derivedCertificate
    {mesh : MeshCertificate}
    (F : Affine2) (hdet : F.linearDet ≠ 0)
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
    RT0P1DerivedAssemblyCertificate mesh :=
  RT0P1DerivedAssemblyCertificate.ofExactElements
    (fun K => F.mapTriangle (triangle K))
    (fun K => pullP1 F (primal K))
    (fun K => piolaRT0 F (flux K))
    (by
      intro K
      rw [cellDivergence_map F (triangle K) (primal K) (flux K) hdet]
      exact hEquilibrium K)
    (by
      intro b
      rw [localFacePairing_map F
        (triangle (mesh.boundaryCell b))
        (primal (mesh.boundaryCell b))
        (flux (mesh.boundaryCell b))
        (mesh.boundarySlot b) hdet]
      exact hBoundary b)
    (by
      intro i
      rw [localFacePairing_map F
        (triangle (mesh.interiorLeftCell i))
        (primal (mesh.interiorLeftCell i))
        (flux (mesh.interiorLeftCell i))
        (mesh.interiorLeftSlot i) hdet]
      rw [localFacePairing_map F
        (triangle (mesh.interiorRightCell i))
        (primal (mesh.interiorRightCell i))
        (flux (mesh.interiorRightCell i))
        (mesh.interiorRightSlot i) hdet]
      exact hInterior i)

/-- The entire transported exact assembly remains orthogonal. -/
theorem orthogonality
    {mesh : MeshCertificate}
    (F : Affine2) (hdet : F.linearDet ≠ 0)
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
    (∑ K : Fin mesh.triangleCount,
      P1RT0Element.cellPairing
        (F.mapTriangle (triangle K))
        (pullP1 F (primal K))
        (piolaRT0 F (flux K))) = 0 := by
  have h := RT0P1DerivedAssemblyCertificate.orthogonality
    (derivedCertificate F hdet triangle primal flux
      hEquilibrium hBoundary hInterior)
  simpa [derivedCertificate, RT0P1DerivedAssemblyCertificate.ofExactElements] using h

/-- Nine-layer endpoint: an exact affine-transported P1/RT0 assembly feeds the
existing discrete Prager--Synge theorem without adding an orthogonality axiom. -/
theorem discrete_prager_synge
    {mesh : MeshCertificate}
    (F : Affine2) (hdet : F.linearDet ≠ 0)
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
          (mesh.interiorRightSlot i) = 0)
    {E : Type*} [SeminormedAddCommGroup E] [InnerProductSpace ℝ E]
    (eGrad eFlux : E)
    (hInner : inner ℝ eGrad eFlux =
      ∑ K : Fin mesh.triangleCount,
        P1RT0Element.cellPairing
          (F.mapTriangle (triangle K))
          (pullP1 F (primal K))
          (piolaRT0 F (flux K))) :
    ‖eGrad + eFlux‖ * ‖eGrad + eFlux‖ =
      ‖eGrad‖ * ‖eGrad‖ + ‖eFlux‖ * ‖eFlux‖ := by
  let cert := derivedCertificate F hdet triangle primal flux
    hEquilibrium hBoundary hInterior
  apply discrete_prager_synge_of_derived_rt0_p1_assembly cert eGrad eFlux
  simpa [cert, derivedCertificate, RT0P1DerivedAssemblyCertificate.ofExactElements] using hInner

end AffineAssemblyTransport

end CACEFormal
