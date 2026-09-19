import Mathlib
import CACEFormal.ReferenceSimplexTopFacetJacobian

namespace CACEFormal

open Set
open scoped BigOperators RealInnerProductSpace

namespace Continuum

noncomputable section

/-!
# Exact flux-factor cancellation on the reference top facet

The top endpoint parameterization has positive surface Jacobian factor
`normDet(L_i)`, while the positive outward normal coordinate is `n_i`.

Previous layers proved

  normDet(L_i)^2 = d,
  d * n_i^2 = 1.

Because both factors are strictly positive, their product is exactly one:

  normDet(L_i) * n_i = 1.

This is the coefficient cancellation needed by the Gauss--Green boundary
current; no explicit `sqrt d` formula is required.
-/

/-- Surface Jacobian times the matching top normal component is exactly one. -/
theorem referenceSimplex_topFacetFluxFactor_eq_one
    {d : Nat} [NeZero d] (i : Fin d) :
    (referenceSimplexTopLinearMap i).normDet *
      simplexFacetOutwardNormalComponent
        (referenceGeometricSimplex d) 0 i = 1 := by
  let J := (referenceSimplexTopLinearMap i).normDet
  let n :=
    simplexFacetOutwardNormalComponent
      (referenceGeometricSimplex d) 0 i
  have hJ2 : J ^ 2 = (d : ℝ) := by
    simpa [J] using referenceSimplexTopLinearMap_normDet_sq i
  have hn2 : (d : ℝ) * n ^ 2 = 1 := by
    simpa [n] using referenceSimplex_topFacetOutwardNormalComponent_sq i
  have hJpos : 0 < J := by
    simpa [J] using referenceSimplexTopLinearMap_normDet_pos i
  have hnpos : 0 < n := by
    simpa [n] using referenceSimplex_topFacetOutwardNormalComponent_pos i
  have hprod2 : (J * n) ^ 2 = 1 := by
    rw [mul_pow, hJ2]
    exact hn2
  have hprodpos : 0 < J * n := mul_pos hJpos hnpos
  have hprod : J * n = 1 := by
    nlinarith
  simpa [J, n] using hprod


end

end Continuum

end CACEFormal
