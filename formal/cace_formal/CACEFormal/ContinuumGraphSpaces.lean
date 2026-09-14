import CACEFormal.ContinuumSobolev

namespace CACEFormal

open scoped BigOperators LineDeriv SchwartzMap

namespace Continuum

/-- The whole-space `L²` Sobolev class, bundled as a complex linear subspace of tempered distributions. -/
def L2Submodule (n : Nat) : Submodule ℂ (ScalarDistribution n) where
  carrier := {u | InL2 u}
  zero_mem' := by
    change TemperedDistribution.MemSobolev
      (E := EuclideanDomain n) (F := ℂ) (0 : ℝ) 2 (0 : ScalarDistribution n)
    exact TemperedDistribution.memSobolev_fun_zero (EuclideanDomain n) ℂ (0 : ℝ) 2
  add_mem' := by
    intro u v hu hv
    change TemperedDistribution.MemSobolev
      (E := EuclideanDomain n) (F := ℂ) (0 : ℝ) 2 u at hu
    change TemperedDistribution.MemSobolev
      (E := EuclideanDomain n) (F := ℂ) (0 : ℝ) 2 v at hv
    change TemperedDistribution.MemSobolev
      (E := EuclideanDomain n) (F := ℂ) (0 : ℝ) 2 (u + v)
    exact hu.add hv
  smul_mem' := by
    intro c u hu
    change TemperedDistribution.MemSobolev
      (E := EuclideanDomain n) (F := ℂ) (0 : ℝ) 2 u at hu
    change TemperedDistribution.MemSobolev
      (E := EuclideanDomain n) (F := ℂ) (0 : ℝ) 2 (c • u)
    exact TemperedDistribution.MemSobolev.smul c hu

/-- The actual Bessel-potential `H¹` class, bundled as a complex linear subspace. -/
def H1Submodule (n : Nat) : Submodule ℂ (ScalarDistribution n) where
  carrier := {u | InH1 u}
  zero_mem' := by
    change TemperedDistribution.MemSobolev
      (E := EuclideanDomain n) (F := ℂ) (1 : ℝ) 2 (0 : ScalarDistribution n)
    exact TemperedDistribution.memSobolev_fun_zero (EuclideanDomain n) ℂ (1 : ℝ) 2
  add_mem' := by
    intro u v hu hv
    change TemperedDistribution.MemSobolev
      (E := EuclideanDomain n) (F := ℂ) (1 : ℝ) 2 u at hu
    change TemperedDistribution.MemSobolev
      (E := EuclideanDomain n) (F := ℂ) (1 : ℝ) 2 v at hv
    change TemperedDistribution.MemSobolev
      (E := EuclideanDomain n) (F := ℂ) (1 : ℝ) 2 (u + v)
    exact hu.add hv
  smul_mem' := by
    intro c u hu
    change TemperedDistribution.MemSobolev
      (E := EuclideanDomain n) (F := ℂ) (1 : ℝ) 2 u at hu
    change TemperedDistribution.MemSobolev
      (E := EuclideanDomain n) (F := ℂ) (1 : ℝ) 2 (c • u)
    exact TemperedDistribution.MemSobolev.smul c hu

@[simp]
theorem weakPartial_zero {n : Nat} (i : Fin n) :
    weakPartial i (0 : ScalarDistribution n) = 0 := by
  simp [weakPartial, LineDeriv.lineDerivOp_zero]

@[simp]
theorem weakPartial_add {n : Nat} (i : Fin n) (u v : ScalarDistribution n) :
    weakPartial i (u + v) = weakPartial i u + weakPartial i v := by
  simp [weakPartial, LineDeriv.lineDerivOp_add]

@[simp]
theorem weakPartial_smul {n : Nat} (i : Fin n) (c : ℂ) (u : ScalarDistribution n) :
    weakPartial i (c • u) = c • weakPartial i u := by
  simp [weakPartial, LineDeriv.lineDerivOp_smul]

/-- Coordinate weak differentiation is a complex linear map on tempered distributions. -/
noncomputable def weakPartialLinearMap {n : Nat} (i : Fin n) :
    ScalarDistribution n →ₗ[ℂ] ScalarDistribution n where
  toFun := weakPartial i
  map_add' := weakPartial_add i
  map_smul' := weakPartial_smul i

@[simp]
theorem distributionalDivergence_zero {n : Nat} :
    distributionalDivergence (0 : VectorDistribution n) = 0 := by
  simp [distributionalDivergence]

@[simp]
theorem distributionalDivergence_add {n : Nat}
    (q r : VectorDistribution n) :
    distributionalDivergence (q + r) =
      distributionalDivergence q + distributionalDivergence r := by
  simp [distributionalDivergence, Finset.sum_add_distrib]

@[simp]
theorem distributionalDivergence_smul {n : Nat}
    (c : ℂ) (q : VectorDistribution n) :
    distributionalDivergence (c • q) = c • distributionalDivergence q := by
  simp [distributionalDivergence, Finset.smul_sum]

/-- Distributional divergence as a complex linear map. -/
noncomputable def distributionalDivergenceLinearMap (n : Nat) :
    VectorDistribution n →ₗ[ℂ] ScalarDistribution n where
  toFun := distributionalDivergence
  map_add' := distributionalDivergence_add
  map_smul' := distributionalDivergence_smul

/-- Whole-space distributional `H(div)` bundled as a complex graph subspace. -/
def HDivSubmodule (n : Nat) : Submodule ℂ (VectorDistribution n) where
  carrier := {q | InHDiv q}
  zero_mem' := by
    constructor
    · intro i
      exact (L2Submodule n).zero_mem
    · rw [distributionalDivergence_zero]
      change TemperedDistribution.MemSobolev
        (E := EuclideanDomain n) (F := ℂ) (0 : ℝ) 2 (0 : ScalarDistribution n)
      exact TemperedDistribution.memSobolev_fun_zero (EuclideanDomain n) ℂ (0 : ℝ) 2
  add_mem' := by
    intro q r hq hr
    constructor
    · intro i
      exact (L2Submodule n).add_mem (hq.1 i) (hr.1 i)
    · rw [distributionalDivergence_add]
      exact (L2Submodule n).add_mem hq.2 hr.2
  smul_mem' := by
    intro c q hq
    constructor
    · intro i
      exact (L2Submodule n).smul_mem c (hq.1 i)
    · rw [distributionalDivergence_smul]
      exact (L2Submodule n).smul_mem c hq.2

/-- Bundled `L²` distributions. -/
abbrev L2Field (n : Nat) := ↥(L2Submodule n)

/-- Bundled whole-space Bessel-potential `H¹` fields. -/
abbrev H1Field (n : Nat) := ↥(H1Submodule n)

/-- Bundled whole-space distributional `H(div)` fields. -/
abbrev HDivField (n : Nat) := ↥(HDivSubmodule n)

/-- Every bundled H¹ field has a bundled L² representative at the distribution level. -/
def H1Field.toL2 {n : Nat} (u : H1Field n) : L2Field n :=
  ⟨u.1, h1_l2 u.2⟩

/-- Every weak coordinate derivative of a bundled H¹ field is bundled L². -/
noncomputable def H1Field.weakPartialL2 {n : Nat} (u : H1Field n) (i : Fin n) : L2Field n :=
  ⟨weakPartial i u.1, h1_weakPartial_l2 u.2 i⟩

/-- The divergence carried by a bundled H(div) field is bundled L². -/
noncomputable def HDivField.divergenceL2 {n : Nat} (q : HDivField n) : L2Field n :=
  ⟨distributionalDivergence q.1, q.2.2⟩

/-- Regression theorem: the zero vector field belongs to every finite-dimensional H(div) graph space. -/
theorem zero_mem_hdiv_graph (n : Nat) :
    (0 : VectorDistribution n) ∈ HDivSubmodule n :=
  (HDivSubmodule n).zero_mem

end Continuum

end CACEFormal
