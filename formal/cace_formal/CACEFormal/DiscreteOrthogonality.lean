import Mathlib
import CACEFormal.DiscretePragerSynge

namespace CACEFormal

open scoped BigOperators

/--
Finite-mesh algebraic bridge.

`cellPairing` is the elementwise contribution to the primal/dual pairing.
`cellDivergence` is the volume term produced by elementwise Green.
`boundaryPairing` is the physical-boundary term.
`interiorFacePairing` is the assembled interior-face contribution.

When the piecewise Green identity holds and equilibrium, boundary admissibility,
and interior-face cancellation annihilate the three right-hand families,
the global pairing is zero.
-/
theorem mesh_admissibility_to_orthogonality
    {Cell Face : Type*} [Fintype Cell] [Fintype Face]
    (cellPairing cellDivergence boundaryPairing : Cell → ℝ)
    (interiorFacePairing : Face → ℝ)
    (hGreen :
      (∑ K, cellPairing K) =
        (∑ K, cellDivergence K) +
        (∑ K, boundaryPairing K) +
        (∑ F, interiorFacePairing F))
    (hEquilibrium : ∀ K, cellDivergence K = 0)
    (hBoundary : ∀ K, boundaryPairing K = 0)
    (hFaces : ∀ F, interiorFacePairing F = 0) :
    (∑ K, cellPairing K) = 0 := by
  rw [hGreen]
  simp [hEquilibrium, hBoundary, hFaces]

/--
Discrete Prager–Synge after the finite-mesh bridge has derived orthogonality.
The remaining geometry-specific burden is to instantiate `hGreen`,
`hEquilibrium`, `hBoundary`, and `hFaces` from the certified mesh/RT data.
-/
theorem discrete_prager_synge_from_mesh_admissibility
    {E Cell Face : Type*}
    [SeminormedAddCommGroup E] [InnerProductSpace ℝ E]
    [Fintype Cell] [Fintype Face]
    (eGrad eFlux : E)
    (cellPairing cellDivergence boundaryPairing : Cell → ℝ)
    (interiorFacePairing : Face → ℝ)
    (hInner : inner ℝ eGrad eFlux = ∑ K, cellPairing K)
    (hGreen :
      (∑ K, cellPairing K) =
        (∑ K, cellDivergence K) +
        (∑ K, boundaryPairing K) +
        (∑ F, interiorFacePairing F))
    (hEquilibrium : ∀ K, cellDivergence K = 0)
    (hBoundary : ∀ K, boundaryPairing K = 0)
    (hFaces : ∀ F, interiorFacePairing F = 0) :
    ‖eGrad + eFlux‖ * ‖eGrad + eFlux‖ =
      ‖eGrad‖ * ‖eGrad‖ + ‖eFlux‖ * ‖eFlux‖ := by
  have hsum : (∑ K, cellPairing K) = 0 :=
    mesh_admissibility_to_orthogonality
      cellPairing cellDivergence boundaryPairing interiorFacePairing
      hGreen hEquilibrium hBoundary hFaces
  have horth : inner ℝ eGrad eFlux = 0 := by
    rw [hInner, hsum]
  exact discrete_prager_synge_of_orthogonality eGrad eFlux horth


/--
Source-aligned finite-mesh Green bridge.

This statement matches the exact checker convention used by
`p1_rt0_green_exact.py`:
  volume pairing + divergence pairing = boundary pairing + interior-face pairing.

It deliberately does not assert that an arbitrary runtime artifact inhabits a
continuum H¹/H(div) graph space.  That geometric embedding remains a separate
formal obligation.
-/
theorem mesh_green_residual_to_orthogonality
    {Cell Face : Type*} [Fintype Cell] [Fintype Face]
    (cellPairing cellDivergence boundaryPairing : Cell → ℝ)
    (interiorFacePairing : Face → ℝ)
    (hGreen :
      (∑ K, cellPairing K) + (∑ K, cellDivergence K) =
        (∑ K, boundaryPairing K) + (∑ F, interiorFacePairing F))
    (hEquilibrium : ∀ K, cellDivergence K = 0)
    (hBoundary : ∀ K, boundaryPairing K = 0)
    (hFaces : ∀ F, interiorFacePairing F = 0) :
    (∑ K, cellPairing K) = 0 := by
  simpa [hEquilibrium, hBoundary, hFaces] using hGreen

/--
Discrete Prager–Synge using the same Green-residual sign convention as the
exact rational P1/RT0 executable checker.
-/
theorem discrete_prager_synge_from_green_residual
    {E Cell Face : Type*}
    [SeminormedAddCommGroup E] [InnerProductSpace ℝ E]
    [Fintype Cell] [Fintype Face]
    (eGrad eFlux : E)
    (cellPairing cellDivergence boundaryPairing : Cell → ℝ)
    (interiorFacePairing : Face → ℝ)
    (hInner : inner ℝ eGrad eFlux = ∑ K, cellPairing K)
    (hGreen :
      (∑ K, cellPairing K) + (∑ K, cellDivergence K) =
        (∑ K, boundaryPairing K) + (∑ F, interiorFacePairing F))
    (hEquilibrium : ∀ K, cellDivergence K = 0)
    (hBoundary : ∀ K, boundaryPairing K = 0)
    (hFaces : ∀ F, interiorFacePairing F = 0) :
    ‖eGrad + eFlux‖ * ‖eGrad + eFlux‖ =
      ‖eGrad‖ * ‖eGrad‖ + ‖eFlux‖ * ‖eFlux‖ := by
  have hsum : (∑ K, cellPairing K) = 0 :=
    mesh_green_residual_to_orthogonality
      cellPairing cellDivergence boundaryPairing interiorFacePairing
      hGreen hEquilibrium hBoundary hFaces
  have horth : inner ℝ eGrad eFlux = 0 := by
    rw [hInner, hsum]
  exact discrete_prager_synge_of_orthogonality eGrad eFlux horth

end CACEFormal
