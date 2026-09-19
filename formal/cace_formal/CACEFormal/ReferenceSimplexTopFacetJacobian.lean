import Mathlib
import CACEFormal.ReferenceSimplexTopFacetParameterization

namespace CACEFormal

open Set
open scoped BigOperators RealInnerProductSpace

namespace Continuum

noncomputable section

/-!
# Jacobian of the reference top-facet parameterization

For coordinate `i`, the linear part of the upper-endpoint graph map is

  L_i(y) = y - (Σ_j y_j) e_i

on `S_i = (ℝ ∙ e_i)ᗮ`.

The coordinate-sum functional is represented, via the inner product on
`S_i`, by the vector

  w_i = Σ_{j ≠ i} e_j.

Hence

  ⟪L_i x, L_i y⟫ = ⟪x,y⟫ + ⟪w_i,x⟫ ⟪w_i,y⟫.

In an arbitrary orthonormal basis of `S_i`, the Gram matrix is therefore
`I + u uᵀ`.  Mathlib's matrix determinant lemma gives

  normDet(L_i)^2 = 1 + ‖w_i‖^2 = d.

This is the exact surface-Jacobian square needed by the flux-measure proof.
-/

/-- Sum of all nonselected coordinate basis vectors, as an element of `e_iᗮ`. -/
noncomputable def referenceSimplexTopSumVector
    {d : Nat} (i : Fin d) :
    (referenceSimplexCoordinateLine i)ᗮ :=
  ⟨∑ j ∈ Finset.univ.erase i, basisVector j, by
    apply
      (mem_referenceSimplexCoordinateLine_orthogonal_iff i _).2
    simp [basisVector, PiLp.single_apply]⟩

/-- The selected coordinate of the top sum vector vanishes. -/
@[simp]
theorem referenceSimplexTopSumVector_proj_same
    {d : Nat} (i : Fin d) :
    EuclideanSpace.proj i
      (referenceSimplexTopSumVector i : EuclideanDomain d) = 0 := by
  simp [referenceSimplexTopSumVector, basisVector, PiLp.single_apply]

/-- Every nonselected coordinate of the top sum vector is one. -/
theorem referenceSimplexTopSumVector_proj_ne
    {d : Nat} (i j : Fin d) (hji : j ≠ i) :
    EuclideanSpace.proj j
      (referenceSimplexTopSumVector i : EuclideanDomain d) = 1 := by
  simp [referenceSimplexTopSumVector, basisVector, PiLp.single_apply, hji]

/-- The top sum vector has squared norm `d - 1`. -/
theorem referenceSimplexTopSumVector_norm_sq
    {d : Nat} [NeZero d] (i : Fin d) :
    ‖referenceSimplexTopSumVector i‖ ^ 2 = (d - 1 : Nat) := by
  have h :=
    EuclideanSpace.real_norm_sq_eq
      (referenceSimplexTopSumVector i : EuclideanDomain d)
  rw [h]
  rw [← Finset.sum_erase_add Finset.univ
    (fun j : Fin d =>
      (EuclideanSpace.proj j
        (referenceSimplexTopSumVector i : EuclideanDomain d)) ^ 2)
    (Finset.mem_univ i)]
  simp [referenceSimplexTopSumVector_proj_same,
    referenceSimplexTopSumVector_proj_ne]

/-- Coordinate sum on the base hyperplane is inner product with the top sum vector. -/
theorem referenceSimplexCoordinateSumLinearMap_eq_inner
    {d : Nat} (i : Fin d)
    (y : (referenceSimplexCoordinateLine i)ᗮ) :
    referenceSimplexCoordinateSumLinearMap i y =
      ⟪referenceSimplexTopSumVector i, y⟫_ℝ := by
  rw [referenceSimplexCoordinateSumLinearMap_apply]
  have hi := referenceSimplexBase_proj_eq_zero i y
  rw [← Finset.sum_erase_add Finset.univ
    (fun j : Fin d => EuclideanSpace.proj j (y : EuclideanDomain d))
    (Finset.mem_univ i)]
  rw [hi, add_zero]
  simp [referenceSimplexTopSumVector, inner_sum,
    basisVector, EuclideanSpace.inner_single_left]

/-- Gram identity for the linear top-endpoint map. -/
theorem referenceSimplexTopLinearMap_inner
    {d : Nat} (i : Fin d)
    (x y : (referenceSimplexCoordinateLine i)ᗮ) :
    ⟪referenceSimplexTopLinearMap i x,
      referenceSimplexTopLinearMap i y⟫_ℝ =
      ⟪x, y⟫_ℝ +
        referenceSimplexCoordinateSumLinearMap i x *
          referenceSimplexCoordinateSumLinearMap i y := by
  have hxi := referenceSimplexBase_proj_eq_zero i x
  have hyi := referenceSimplexBase_proj_eq_zero i y
  rw [referenceSimplexTopLinearMap_apply,
    referenceSimplexTopLinearMap_apply]
  simp [inner_sub_left, inner_sub_right, inner_smul_left,
    inner_smul_right, basisVector, EuclideanSpace.inner_single_left,
    EuclideanSpace.inner_single_right, hxi, hyi]
  ring

/-- Parseval evaluates the rank-one Gram contribution as `d - 1`. -/
theorem referenceSimplexTopCoordinateSum_parseval
    {d : Nat} [NeZero d] (i : Fin d) :
    let S := (referenceSimplexCoordinateLine i)ᗮ
    let b := stdOrthonormalBasis ℝ S
    ∑ a : Fin (Module.finrank ℝ S),
      (referenceSimplexCoordinateSumLinearMap i (b a)) ^ 2 =
        (d - 1 : Nat) := by
  dsimp
  let S := (referenceSimplexCoordinateLine i)ᗮ
  let b := stdOrthonormalBasis ℝ S
  let w : S := referenceSimplexTopSumVector i
  have hp := b.sum_sq_inner_left w
  have hnorm :
      ‖w‖ ^ 2 = (d - 1 : Nat) := by
    simpa [S, w] using referenceSimplexTopSumVector_norm_sq i
  rw [hnorm] at hp
  simpa [S, b, w, referenceSimplexCoordinateSumLinearMap_eq_inner]
    using hp

/-- The top-endpoint linear map has squared norm determinant exactly `d`. -/
theorem referenceSimplexTopLinearMap_normDet_sq
    {d : Nat} [NeZero d] (i : Fin d) :
    (referenceSimplexTopLinearMap i).normDet ^ 2 = (d : ℝ) := by
  let S := (referenceSimplexCoordinateLine i)ᗮ
  let L : S →ₗ[ℝ] EuclideanDomain d :=
    referenceSimplexTopLinearMap i
  let b := stdOrthonormalBasis ℝ S
  let u : Fin (Module.finrank ℝ S) → ℝ :=
    fun a => referenceSimplexCoordinateSumLinearMap i (b a)
  have hgram :
      Matrix.gram ℝ (fun a => L (b a)) =
        1 +
          Matrix.replicateCol Unit u *
            Matrix.replicateRow Unit u := by
    ext a c
    rw [Matrix.gram_apply]
    rw [show L (b a) = referenceSimplexTopLinearMap i (b a) by rfl]
    rw [show L (b c) = referenceSimplexTopLinearMap i (b c) by rfl]
    rw [referenceSimplexTopLinearMap_inner]
    have horth :=
      (orthonormal_iff_ite.mp b.orthonormal) a c
    rw [horth]
    simp [u, Matrix.mul_apply]
  have hparseval :
      ∑ a : Fin (Module.finrank ℝ S), (u a) ^ 2 =
        (d - 1 : Nat) := by
    simpa [S, b, u] using
      referenceSimplexTopCoordinateSum_parseval i
  have hdot :
      u ⬝ᵥ u = (d - 1 : Nat) := by
    rw [Matrix.dotProduct]
    simpa [pow_two] using hparseval
  have hdet :
      (Matrix.gram ℝ (fun a => L (b a))).det = (d : ℝ) := by
    rw [hgram,
      Matrix.det_one_add_replicateCol_mul_replicateRow
        (ι := Unit) u u,
      hdot]
    have hd : 1 ≤ d := Nat.one_le_iff_ne_zero.mpr (NeZero.ne d)
    push_cast [Nat.cast_sub hd]
    ring
  have hnorm :=
    LinearMap.normDet_sq_eq_det_gram L b
  rw [hdet] at hnorm
  simpa [L] using hnorm

/-- The top-endpoint linear map has strictly positive norm determinant. -/
theorem referenceSimplexTopLinearMap_normDet_pos
    {d : Nat} [NeZero d] (i : Fin d) :
    0 < (referenceSimplexTopLinearMap i).normDet := by
  have hsquare := referenceSimplexTopLinearMap_normDet_sq i
  have hd : (0 : ℝ) < d := by
    exact_mod_cast Nat.pos_of_ne_zero (NeZero.ne d)
  have hnonneg := LinearMap.normDet_nonneg (referenceSimplexTopLinearMap i)
  nlinarith

end

end Continuum

end CACEFormal
