import Mathlib
import CACEFormal.Generated.RuntimeP1RT0BindingFixture
import CACEFormal.MeshElementGeometry
import CACEFormal.PhysicalP1RT0Element

namespace CACEFormal.Generated

open CACEFormal

/-!
FSL-5 quarantined local-semantics bridge for the deterministic runtime packet fixture.

This module does not assert equilibrium, boundary admissibility, interior-face
cancellation, global orthogonality, or continuum H¹/H(div) membership.  It only
connects the exact generated MeshCertificate/P1Affine/RT0Affine objects to the
already-proved exact physical element Green identity.
-/

/-- The generated runtime triangle is exactly the certified mesh geometry. -/
theorem runtimeP1RT0Fixture_det_is_certified
    (K : Fin runtimeP1RT0FixtureMesh.triangleCount) :
    (MeshElementGeometry.realTriangle runtimeP1RT0FixtureMesh K).det =
      (runtimeP1RT0FixtureMesh.signedJacobian K : ℝ) :=
  MeshElementGeometry.realTriangle_det runtimeP1RT0FixtureMesh K

/--
Every generated P1/RT0 cell satisfies the exact positive-orientation physical
Green identity.  The local identity is derived by the formal element theorem;
it is not stored as a caller-supplied runtime assertion.
-/
theorem runtimeP1RT0Fixture_local_green
    (K : Fin runtimeP1RT0FixtureMesh.triangleCount) :
    PhysicalP1RT0Element.cellPairing
        (MeshElementGeometry.realTriangle runtimeP1RT0FixtureMesh K)
        (runtimeP1RT0FixtureP1 K)
        (runtimeP1RT0FixtureRT0 K) =
      PhysicalP1RT0Element.cellDivergence
          (MeshElementGeometry.realTriangle runtimeP1RT0FixtureMesh K)
          (runtimeP1RT0FixtureP1 K)
          (runtimeP1RT0FixtureRT0 K) +
        P1RT0Element.cellFacePairing
          (MeshElementGeometry.realTriangle runtimeP1RT0FixtureMesh K)
          (runtimeP1RT0FixtureP1 K)
          (runtimeP1RT0FixtureRT0 K) :=
  PhysicalP1RT0Element.mesh_local_green_identity
    runtimeP1RT0FixtureMesh K
    (runtimeP1RT0FixtureP1 K)
    (runtimeP1RT0FixtureRT0 K)

/-- Oriented algebraic form of the same local identity. -/
theorem runtimeP1RT0Fixture_oriented_local_green
    (K : Fin runtimeP1RT0FixtureMesh.triangleCount) :
    P1RT0Element.cellPairing
        (MeshElementGeometry.realTriangle runtimeP1RT0FixtureMesh K)
        (runtimeP1RT0FixtureP1 K)
        (runtimeP1RT0FixtureRT0 K) =
      P1RT0Element.cellDivergence
          (MeshElementGeometry.realTriangle runtimeP1RT0FixtureMesh K)
          (runtimeP1RT0FixtureP1 K)
          (runtimeP1RT0FixtureRT0 K) +
        P1RT0Element.cellFacePairing
          (MeshElementGeometry.realTriangle runtimeP1RT0FixtureMesh K)
          (runtimeP1RT0FixtureP1 K)
          (runtimeP1RT0FixtureRT0 K) :=
  P1RT0Element.local_green_identity
    (MeshElementGeometry.realTriangle runtimeP1RT0FixtureMesh K)
    (runtimeP1RT0FixtureP1 K)
    (runtimeP1RT0FixtureRT0 K)

end CACEFormal.Generated
