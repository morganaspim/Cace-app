import Mathlib
import CACEFormal.SimplexAffineL2
import CACEFormal.PDEDomainBridge

namespace CACEFormal

open Set MeasureTheory
open scoped LineDeriv SchwartzMap

namespace Continuum

noncomputable section

/-!
# Simplex boundary distributions

This layer fixes the distributional sign convention before the geometric
integration-by-parts proof. Mathlib defines the directional derivative of a
tempered distribution by precomposition with the negative directional
derivative of the Schwartz test function.

The boundary term is explicit. Mesh cancellation is a later theorem.
-/

abbrev SimplexScalarDistribution (d : Nat) := 𝓢'(SimplexPoint d, ℂ)

/-- Coordinate vector in the ambient finite-dimensional simplex space. -/
def simplexBasisVector {d : Nat} (i : Fin d) : SimplexPoint d :=
  fun j => if j = i then 1 else 0

/-- Mathlib sign convention: (partial_i T)(phi) = - T(partial_i phi). -/
theorem simplex_distributional_partial_apply {d : Nat}
    (i : Fin d) (T : SimplexScalarDistribution d) (φ : 𝓢(SimplexPoint d, ℂ)) :
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

end

end Continuum

end CACEFormal
