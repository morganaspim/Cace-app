import CACEFormal.BoxGraphGreenPairing
import CACEFormal.RT0P1DerivedAssembly

namespace CACEFormal

open scoped BigOperators

namespace Continuum

noncomputable section

/-!
# Exact finite-mesh to bounded-box Green-pairing interface

This file isolates the remaining representation burden between the exact P1/RT0
finite-element certificate and the bounded-box H¹/H(div) graph model.

No claim is made here that arbitrary Python data inhabit the graph spaces.
Instead, the two coordinate-identification hypotheses below state exactly what
a concrete mesh-to-L² embedding must prove.  Once those hypotheses are supplied,
the existing kernel-checked assembly theorems force the bounded-box volume
pairing to vanish under the certificate's equilibrium/admissibility conditions.
-/

/--
A complete exact RT0/P1 assembly certificate annihilates the bounded-box Green
volume pairing once its finite element cell terms are identified with the two
L² coordinate contributions of the closed graph points.

The sign in `hDivValue` is intentional:
`P1RT0Element.cellDivergence` stores `-∫ (div q) v`, whereas the graph
pairing stores `+∫ (div q) v`.
-/
theorem box_volumePairing_eq_zero_of_rt0_p1_representation
    {n : Nat} (a b : BoxPoint n)
    {mesh : MeshCertificate}
    (cert : RT0P1DerivedAssemblyCertificate mesh)
    (q : BoxHDivGraphClosedSpace a b)
    (v : BoxH1GraphClosedSpace a b)
    (hFieldGrad :
      (∑ i : Fin (n + 1), inner ℝ (q.1.1 i) (v.1.2 i)) =
        ∑ K : Fin mesh.triangleCount, cert.cellPairing K)
    (hDivValue :
      inner ℝ q.1.2 v.1.1 =
        -(∑ K : Fin mesh.triangleCount, cert.cellDivergence K)) :
    (boxGraphBoundedGreenPairing a b).volumePairing q v = 0 := by
  rw [show
    (boxGraphBoundedGreenPairing a b).volumePairing q v =
      (∑ i : Fin (n + 1), inner ℝ (q.1.1 i) (v.1.2 i)) +
        inner ℝ q.1.2 v.1.1 by
      exact closedBoxGraphGreenPairing_apply a b q v]
  rw [hFieldGrad, hDivValue]
  have hpair :
      (∑ K : Fin mesh.triangleCount, cert.cellPairing K) = 0 :=
    RT0P1DerivedAssemblyCertificate.orthogonality cert
  have hdiv :
      (∑ K : Fin mesh.triangleCount, cert.cellDivergence K) = 0 := by
    apply Finset.sum_eq_zero
    intro K _
    exact cert.equilibrium K
  rw [hpair, hdiv]
  norm_num

/--
The same representation hypotheses provide the exact cross-term value required
by the continuum Prager–Synge interface when the Hilbert error cross term is
identified with the finite P1/RT0 cell-pairing sum.

This theorem deliberately keeps `hInner` explicit: constructing the actual
error vectors and proving that their Hilbert inner product is the assembled
finite-element pairing is a separate source-to-formal obligation.
-/
theorem box_crossTerm_eq_volumePairing_of_rt0_p1_representation
    {n : Nat} (a b : BoxPoint n)
    {mesh : MeshCertificate}
    (cert : RT0P1DerivedAssemblyCertificate mesh)
    (q : BoxHDivGraphClosedSpace a b)
    (v : BoxH1GraphClosedSpace a b)
    {E : Type*} [SeminormedAddCommGroup E] [InnerProductSpace ℝ E]
    (eGrad eFlux : E)
    (hInner :
      inner ℝ eGrad eFlux =
        ∑ K : Fin mesh.triangleCount, cert.cellPairing K)
    (hFieldGrad :
      (∑ i : Fin (n + 1), inner ℝ (q.1.1 i) (v.1.2 i)) =
        ∑ K : Fin mesh.triangleCount, cert.cellPairing K)
    (hDivValue :
      inner ℝ q.1.2 v.1.1 =
        -(∑ K : Fin mesh.triangleCount, cert.cellDivergence K)) :
    inner ℝ eGrad eFlux =
      (boxGraphBoundedGreenPairing a b).volumePairing q v := by
  have hvol :
      (boxGraphBoundedGreenPairing a b).volumePairing q v = 0 :=
    box_volumePairing_eq_zero_of_rt0_p1_representation
      a b cert q v hFieldGrad hDivValue
  have hpair :
      (∑ K : Fin mesh.triangleCount, cert.cellPairing K) = 0 :=
    RT0P1DerivedAssemblyCertificate.orthogonality cert
  rw [hInner, hpair, hvol]



/--
Interface-cancellation obligations for a piecewise affine P1/RT0 realization.

These are intentionally stated at the finite mesh level.  P1 trace matching and
oppositely oriented RT0 normal-trace matching are the hypotheses needed to
remove internal distributional boundary terms when the cellwise integration by
parts identities are assembled.
-/
structure P1RT0InterfaceCancellation {mesh : MeshCertificate}
    (triangle : Fin mesh.triangleCount → Triangle2)
    (primal : Fin mesh.triangleCount → P1Affine)
    (flux : Fin mesh.triangleCount → RT0Affine) where
  boundaryZero : ∀ b,
    P1RT0Element.localFacePairing
      (triangle (mesh.boundaryCell b))
      (primal (mesh.boundaryCell b))
      (flux (mesh.boundaryCell b))
      (mesh.boundarySlot b) = 0
  interiorZero : ∀ i,
    P1RT0Element.localFacePairing
        (triangle (mesh.interiorLeftCell i))
        (primal (mesh.interiorLeftCell i))
        (flux (mesh.interiorLeftCell i))
        (mesh.interiorLeftSlot i) +
      P1RT0Element.localFacePairing
        (triangle (mesh.interiorRightCell i))
        (primal (mesh.interiorRightCell i))
        (flux (mesh.interiorRightCell i))
        (mesh.interiorRightSlot i) = 0

/--
Cellwise equilibrium plus interface cancellation constructs the exact assembly
certificate consumed by the bounded-box representation layer.  Thus no
independent global Green identity is assumed at the source-to-formal boundary.
-/
noncomputable def P1RT0InterfaceCancellation.toDerivedCertificate
    {mesh : MeshCertificate}
    (triangle : Fin mesh.triangleCount → Triangle2)
    (primal : Fin mesh.triangleCount → P1Affine)
    (flux : Fin mesh.triangleCount → RT0Affine)
    (hEquilibrium : ∀ K,
      P1RT0Element.cellDivergence (triangle K) (primal K) (flux K) = 0)
    (hInterface : P1RT0InterfaceCancellation triangle primal flux) :
    RT0P1DerivedAssemblyCertificate mesh :=
  RT0P1DerivedAssemblyCertificate.ofExactElements
    triangle primal flux hEquilibrium hInterface.boundaryZero hInterface.interiorZero

/--
Data needed to place a supported finite P1/RT0 realization into the bounded-box
closed graph spaces without conflating the finite certificate with the analytic
embedding proof.

The representative points themselves carry membership in the smooth-core
closures through their types.  The two equalities are the exact analytic
identification obligations left by the finite-element-to-L² passage.
-/
structure P1RT0BoxRepresentation {n : Nat} (a b : BoxPoint n)
    {mesh : MeshCertificate}
    (cert : RT0P1DerivedAssemblyCertificate mesh) where
  hdivPoint : BoxHDivGraphClosedSpace a b
  h1Point : BoxH1GraphClosedSpace a b
  fieldGrad_eq_cellSum :
    (∑ i : Fin (n + 1), inner ℝ (hdivPoint.1.1 i) (h1Point.1.2 i)) =
      ∑ K : Fin mesh.triangleCount, cert.cellPairing K
  divValue_eq_cellDivergenceSum :
    inner ℝ hdivPoint.1.2 h1Point.1.1 =
      -(∑ K : Fin mesh.triangleCount, cert.cellDivergence K)

namespace P1RT0BoxRepresentation

/-- A represented exact assembly certificate has zero bounded-box Green volume pairing. -/
theorem volumePairing_eq_zero {n : Nat} (a b : BoxPoint n)
    {mesh : MeshCertificate}
    (cert : RT0P1DerivedAssemblyCertificate mesh)
    (rep : P1RT0BoxRepresentation a b cert) :
    (boxGraphBoundedGreenPairing a b).volumePairing rep.hdivPoint rep.h1Point = 0 :=
  box_volumePairing_eq_zero_of_rt0_p1_representation
    a b cert rep.hdivPoint rep.h1Point
    rep.fieldGrad_eq_cellSum rep.divValue_eq_cellDivergenceSum

/--
Once the executable/formal error vectors are identified with the same exact
cell-pairing sum, the represented box graph supplies the continuum cross-term
equality required by the Prager–Synge interface.
-/
theorem crossTerm_eq_volumePairing {n : Nat} (a b : BoxPoint n)
    {mesh : MeshCertificate}
    (cert : RT0P1DerivedAssemblyCertificate mesh)
    (rep : P1RT0BoxRepresentation a b cert)
    {E : Type*} [SeminormedAddCommGroup E] [InnerProductSpace ℝ E]
    (eGrad eFlux : E)
    (hInner :
      inner ℝ eGrad eFlux =
        ∑ K : Fin mesh.triangleCount, cert.cellPairing K) :
    inner ℝ eGrad eFlux =
      (boxGraphBoundedGreenPairing a b).volumePairing rep.hdivPoint rep.h1Point :=
  box_crossTerm_eq_volumePairing_of_rt0_p1_representation
    a b cert rep.hdivPoint rep.h1Point eGrad eFlux hInner
    rep.fieldGrad_eq_cellSum rep.divValue_eq_cellDivergenceSum

end P1RT0BoxRepresentation

end

end Continuum

end CACEFormal
