import Mathlib
import CACEFormal.PDEDomainBridge

namespace CACEFormal

open Set MeasureTheory
open scoped BigOperators LineDeriv SchwartzMap

namespace Continuum

noncomputable section

/-!
# Simplex boundary distributions

This layer fixes the distributional sign convention before the geometric
integration-by-parts proof.  It intentionally uses the canonical
`EuclideanDomain d` / `ScalarDistribution d` ambient from the Sobolev and
H¹/H(div) graph machinery, so the later simplex-to-graph bridge does not cross
an unproved change of norm or measure space.

Mathlib defines the directional derivative of a tempered distribution by
precomposition with the negative directional derivative of the Schwartz test
function.  The boundary term is explicit. Mesh cancellation is a later theorem.
-/

abbrev SimplexScalarDistribution (d : Nat) := ScalarDistribution d

/-- Coordinate vector in the canonical Euclidean Sobolev ambient. -/
def simplexBasisVector {d : Nat} (i : Fin d) : EuclideanDomain d :=
  basisVector i

/-- Mathlib sign convention: (partial_i T)(phi) = - T(partial_i phi). -/
theorem simplex_distributional_partial_apply {d : Nat}
    (i : Fin d) (T : SimplexScalarDistribution d) (φ : 𝓢(EuclideanDomain d, ℂ)) :
    (∂_{simplexBasisVector i} T) φ =
      - T (∂_{simplexBasisVector i} φ) := by
  rw [TemperedDistribution.lineDerivOp_apply_apply]
  exact map_neg T (∂_{simplexBasisVector i} φ)

/--
Boundary distribution required by the scalar cellwise integration-by-parts
identity. The next geometric layer constructs this from oriented facets of a
nondegenerate simplex.
-/
structure SimplexScalarBoundaryData {d : Nat}
    (cell : SimplexScalarDistribution d) (interior : Fin d → SimplexScalarDistribution d) where
  boundary : Fin d → SimplexScalarDistribution d
  cellIBP : ∀ i : Fin d,
    ∂_{simplexBasisVector i} cell = interior i - boundary i

/-- Cellwise distributional identity with the boundary term explicit. -/
theorem simplex_scalar_cellwise_distributional_ibp {d : Nat}
    (cell : SimplexScalarDistribution d) (interior : Fin d → SimplexScalarDistribution d)
    (h : SimplexScalarBoundaryData cell interior) (i : Fin d) :
    ∂_{simplexBasisVector i} cell = interior i - h.boundary i :=
  h.cellIBP i


/--
Finite assembly of exact cellwise simplex integration-by-parts identities.
The total boundary distribution remains explicit; no interface cancellation
or boundary-condition assumption is hidden in this theorem.
-/
theorem simplex_cellwise_distributional_ibp_sum
    {Cell : Type*} [Fintype Cell] {d : Nat}
    (cell : Cell → SimplexScalarDistribution d)
    (interior boundary : Cell → Fin d → SimplexScalarDistribution d)
    (hCell : ∀ K i,
      ∂_{simplexBasisVector i} (cell K) =
        interior K i - boundary K i)
    (i : Fin d) :
    ∂_{simplexBasisVector i} (∑ K, cell K) =
      (∑ K, interior K i) - ∑ K, boundary K i := by
  calc
    ∂_{simplexBasisVector i} (∑ K, cell K) =
        ∑ K, ∂_{simplexBasisVector i} (cell K) := by
      simpa using
        (lineDerivOp_sum (simplexBasisVector i) cell Finset.univ)
    _ = ∑ K, (interior K i - boundary K i) := by
      apply Finset.sum_congr rfl
      intro K _
      exact hCell K i
    _ = (∑ K, interior K i) - ∑ K, boundary K i := by
      rw [Finset.sum_sub_distrib]

/--
If the assembled simplex boundary distribution cancels, the finite cellwise
identities reduce to the global weak derivative identity.
-/
theorem simplex_cellwise_distributional_ibp_sum_of_boundary_cancel
    {Cell : Type*} [Fintype Cell] {d : Nat}
    (cell : Cell → SimplexScalarDistribution d)
    (interior boundary : Cell → Fin d → SimplexScalarDistribution d)
    (hCell : ∀ K i,
      ∂_{simplexBasisVector i} (cell K) =
        interior K i - boundary K i)
    (hBoundary : ∀ i, (∑ K, boundary K i) = 0)
    (i : Fin d) :
    ∂_{simplexBasisVector i} (∑ K, cell K) =
      ∑ K, interior K i := by
  rw [simplex_cellwise_distributional_ibp_sum cell interior boundary hCell i,
    hBoundary i, sub_zero]

end

end Continuum

end CACEFormal
