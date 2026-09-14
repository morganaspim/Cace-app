import Mathlib
import CACEFormal.RT0P1Assembly
import CACEFormal.ConcreteMeshCertificate
import CACEFormal.Generated.V323MeshCertificate

namespace CACEFormal.Generated

open CACEFormal
open scoped BigOperators

/-!
The v3.22 fixture uses `V322Cell = Fin 4` and `V322InteriorFace = Fin 4`,
while the generic v3.24 API indexes data by the counts stored in the
v3.23 `MeshCertificate`.  Although those counts reduce to four for this fixture,
we keep the bridge explicit so the instance does not rely on semireducible
structure-field unfolding during typeclass/tactic elaboration.
-/

def v324CellIndex (K : Fin v323SquareCenterMesh.triangleCount) : V322Cell :=
  Fin.cast (by rfl) K


def v324InteriorFaceIndex
    (F : Fin v323SquareCenterMesh.interiorEdgeCount) : V322InteriorFace :=
  Fin.cast (by rfl) F


def v324CellPairing (K : Fin v323SquareCenterMesh.triangleCount) : ℝ :=
  v322CellPairing (v324CellIndex K)


def v324CellDivergence (K : Fin v323SquareCenterMesh.triangleCount) : ℝ :=
  v322CellDivergence (v324CellIndex K)


def v324CellFacePairing (K : Fin v323SquareCenterMesh.triangleCount) : ℝ :=
  v324CellPairing K


def v324BoundaryPairing (K : Fin v323SquareCenterMesh.triangleCount) : ℝ :=
  v322BoundaryPairing (v324CellIndex K)


def v324InteriorFacePairing
    (F : Fin v323SquareCenterMesh.interiorEdgeCount) : ℝ :=
  v322InteriorFacePairing (v324InteriorFaceIndex F)

/--
The already verified v3.22 exact rational fixture, routed through the generic
v3.23 geometry-linked mesh certificate and the v3.24 local-to-global RT0/P1
assembly certificate API.
-/
def v324SquareCenterAssembly : RT0P1AssemblyCertificate v323SquareCenterMesh where
  cellPairing := v324CellPairing
  cellDivergence := v324CellDivergence
  cellFacePairing := v324CellFacePairing
  boundaryPairing := v324BoundaryPairing
  interiorFacePairing := v324InteriorFacePairing
  localGreenIdentity := by
    intro K
    simp [v324CellPairing, v324CellFacePairing, v324CellDivergence,
      v322CellDivergence, v322FluxError]
  faceAssembly := by
    norm_num [Fin.sum_univ_four, v324CellFacePairing, v324CellPairing,
      v324BoundaryPairing, v324InteriorFacePairing, v324CellIndex,
      v324InteriorFaceIndex, v322CellPairing, v322CellArea,
      RationalVector2.dot, v322FluxError, v322CellGradient,
      v322BoundaryPairing, v322InteriorFacePairing,
      v322InteriorFluxCertificate, v322LeftNormalFlux, v322RightNormalFlux]
  equilibrium := by
    intro K
    exact v322_divergence_free (v324CellIndex K)
  boundaryAdmissible := by
    intro K
    exact v322_boundary_terms_zero (v324CellIndex K)
  interiorCancellation := by
    intro F
    exact v322_interior_faces_cancel (v324InteriorFaceIndex F)

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
