import Mathlib
import CACEFormal.DiscreteOrthogonality

namespace CACEFormal

open scoped BigOperators

/-!
v3.22 concrete finite-mesh certificate.

This module intentionally formalizes a small, exact rational fixture before the
general continuum trace theorem.  The represented mesh is the unit square with a
center vertex and four counter-clockwise triangles.  The primal field is P1 by
odal values, the flux-error field is constant per cell (an RT0 subspace in this
fixture), and the interior normal-flux contributions cancel pairwise.
-/

/-- Exact rational 2D point used by generated mesh certificates. -/
structure RationalPoint2 where
  x : ℚ
  y : ℚ
  deriving DecidableEq, Repr

/-- Exact rational 2D vector used for P1 gradients and constant RT0-error fluxes. -/
structure RationalVector2 where
  x : ℚ
  y : ℚ
  deriving DecidableEq, Repr

namespace RationalVector2

def dot (a b : RationalVector2) : ℚ :=
  a.x * b.x + a.y * b.y

end RationalVector2

/-- Vertices of the v3.22 square-with-center certificate. -/
abbrev V322Vertex := Fin 5

/-- Four counter-clockwise triangular cells around the center vertex. -/
abbrev V322Cell := Fin 4

/-- Four physical-boundary edges of the square. -/
abbrev V322BoundaryFace := Fin 4

/-- Four interior radial faces adjacent to the center vertex. -/
abbrev V322InteriorFace := Fin 4

/-- A P1 scalar field represented by exact nodal values. -/
structure P1ScalarField (Vertex : Type*) where
  nodal : Vertex → ℚ

/-- Constant-per-cell flux-error data, the supported RT0 fixture subspace. -/
structure ConstantRT0Error (Cell : Type*) where
  flux : Cell → RationalVector2
  divergence : Cell → ℚ

/-- Interior face certificate with the two oriented normal-flux traces. -/
structure InteriorNormalFluxCertificate where
  leftTrace : ℚ
  rightTrace : ℚ
  cancels : leftTrace + rightTrace = 0

def v322Point (v : V322Vertex) : RationalPoint2 :=
  match v.val with
  | 0 => { x := 0, y := 0 }
  | 1 => { x := 1, y := 0 }
  | 2 => { x := 1, y := 1 }
  | 3 => { x := 0, y := 1 }
  | _ => { x := 1 / 2, y := 1 / 2 }

def v322PrimalP1 : P1ScalarField V322Vertex where
  nodal := fun v =>
    match v.val with
    | 4 => 1
    | _ => 0

def v322FluxError : ConstantRT0Error V322Cell where
  flux := fun _ => { x := 1, y := 0 }
  divergence := fun _ => 0

/-- Exact P1 gradients computed from the four counter-clockwise cells. -/
def v322CellGradient (K : V322Cell) : RationalVector2 :=
  match K.val with
  | 0 => { x := 0, y := 2 }
  | 1 => { x := -2, y := 0 }
  | 2 => { x := 0, y := -2 }
  | _ => { x := 2, y := 0 }

/-- Every cell has area one quarter in this fixture. -/
def v322CellArea (_K : V322Cell) : ℚ :=
  1 / 4

/-- Element contribution `∫_K q · ∇v`, represented exactly. -/
def v322CellPairing (K : V322Cell) : ℝ :=
  (v322CellArea K * RationalVector2.dot (v322FluxError.flux K) (v322CellGradient K) : ℚ)

def v322CellDivergence (K : V322Cell) : ℝ :=
  (v322FluxError.divergence K : ℚ)

/-- Boundary terms vanish because the P1 trace is zero on all four boundary vertices. -/
def v322BoundaryPairing (_K : V322Cell) : ℝ :=
  0

def v322LeftNormalFlux (F : V322InteriorFace) : ℚ :=
  match F.val with
  | 0 => -1 / 2
  | 1 => 1 / 2
  | 2 => -1 / 2
  | _ => -1 / 2

def v322RightNormalFlux (F : V322InteriorFace) : ℚ :=
  match F.val with
  | 0 => 1 / 2
  | 1 => -1 / 2
  | 2 => 1 / 2
  | _ => 1 / 2

def v322InteriorFluxCertificate (F : V322InteriorFace) :
    InteriorNormalFluxCertificate where
  leftTrace := v322LeftNormalFlux F
  rightTrace := v322RightNormalFlux F
  cancels := by
    fin_cases F <;> norm_num [v322LeftNormalFlux, v322RightNormalFlux]

def v322InteriorFacePairing (F : V322InteriorFace) : ℝ :=
  ((v322InteriorFluxCertificate F).leftTrace +
    (v322InteriorFluxCertificate F).rightTrace : ℚ)

theorem v322_boundary_trace_zero (b : V322BoundaryFace) :
    v322PrimalP1.nodal (Fin.castLE (by decide : 4 ≤ 5) b) = 0 := by
  fin_cases b <;> rfl

theorem v322_divergence_free :
    ∀ K : V322Cell, v322CellDivergence K = 0 := by
  intro K
  fin_cases K <;> norm_num [v322CellDivergence, v322FluxError]

theorem v322_boundary_terms_zero :
    ∀ K : V322Cell, v322BoundaryPairing K = 0 := by
  intro K
  fin_cases K <;> rfl

theorem v322_interior_faces_cancel :
    ∀ F : V322InteriorFace, v322InteriorFacePairing F = 0 := by
  intro F
  dsimp [v322InteriorFacePairing]
  rw [(v322InteriorFluxCertificate F).cancels]
  norm_num

theorem v322_cell_pairing_values :
    v322CellPairing 0 = 0 ∧
    v322CellPairing 1 = -(1 / 2 : ℝ) ∧
    v322CellPairing 2 = 0 ∧
    v322CellPairing 3 = (1 / 2 : ℝ) := by
  norm_num [v322CellPairing, v322CellArea, RationalVector2.dot,
    v322FluxError, v322CellGradient]

/-- The exact assembled Green identity for the concrete v3.22 fixture. -/
theorem v322_global_green_identity :
    (∑ K : V322Cell, v322CellPairing K) =
      (∑ K : V322Cell, v322CellDivergence K) +
      (∑ K : V322Cell, v322BoundaryPairing K) +
      (∑ F : V322InteriorFace, v322InteriorFacePairing F) := by
  norm_num [Fin.sum_univ_four, v322CellPairing, v322CellArea,
    RationalVector2.dot, v322FluxError, v322CellGradient,
    v322CellDivergence, v322BoundaryPairing, v322InteriorFacePairing,
    v322InteriorFluxCertificate, v322LeftNormalFlux, v322RightNormalFlux]

/-- Orthogonality is derived from the concrete mesh certificate, not assumed. -/
theorem v322_concrete_mesh_orthogonality :
    (∑ K : V322Cell, v322CellPairing K) = 0 := by
  exact mesh_admissibility_to_orthogonality
    v322CellPairing
    v322CellDivergence
    v322BoundaryPairing
    v322InteriorFacePairing
    v322_global_green_identity
    v322_divergence_free
    v322_boundary_terms_zero
    v322_interior_faces_cancel

/--
Concrete v3.22 endpoint: once the generated Hilbert-space error vectors expose
the same inner-product sum as this exact mesh certificate, the discrete
Prager--Synge identity follows.
-/
theorem v322_discrete_prager_synge_from_concrete_mesh
    {E : Type*} [SeminormedAddCommGroup E] [InnerProductSpace ℝ E]
    (eGrad eFlux : E)
    (hInner : inner ℝ eGrad eFlux = ∑ K : V322Cell, v322CellPairing K) :
    ‖eGrad + eFlux‖ * ‖eGrad + eFlux‖ =
      ‖eGrad‖ * ‖eGrad‖ + ‖eFlux‖ * ‖eFlux‖ := by
  exact discrete_prager_synge_from_mesh_admissibility
    eGrad
    eFlux
    v322CellPairing
    v322CellDivergence
    v322BoundaryPairing
    v322InteriorFacePairing
    hInner
    v322_global_green_identity
    v322_divergence_free
    v322_boundary_terms_zero
    v322_interior_faces_cancel

end CACEFormal
