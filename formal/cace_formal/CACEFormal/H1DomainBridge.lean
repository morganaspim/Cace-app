import CACEFormal.PDEDomainBridge
import CACEFormal.RegularizationClosure

namespace CACEFormal

open Set Finset MeasureTheory Filter
open scoped BigOperators LineDeriv SchwartzMap

namespace Continuum

noncomputable section

/-!
# v3.30 distributional H1 graph bridge

The earlier continuum track had an explicit closed distributional graph relation for H(div), but no
parallel relation for scalar H1 graph data.  This module adds the missing structural half: the
ambient graph coordinates `(u, g)` satisfy `g_i = ∂_i u` as tempered distributions exactly when a
continuous defect map vanishes.

This is intentionally a graph-relation theorem.  It does not silently identify this relation with
Mathlib's Bessel-potential `InH1` predicate; that equivalence remains a separate analytic theorem.
-/

/-- Complex whole-space H1 graph coordinates `(u, g)` with an L2 value and L2 gradient slots. -/
abbrev H1ComplexGraphAmbient (n : Nat) :=
  ComplexL2 n × (Fin n → ComplexL2 n)

/-- Value projection from complex H1 graph data. -/
noncomputable def complexH1ValueProj (n : Nat) :
    H1ComplexGraphAmbient n →L[ℂ] ComplexL2 n :=
  ContinuousLinearMap.fst ℂ (ComplexL2 n) (Fin n → ComplexL2 n)

/-- Gradient-coordinate projection from complex H1 graph data. -/
noncomputable def complexH1GradProj (n : Nat) (i : Fin n) :
    H1ComplexGraphAmbient n →L[ℂ] ComplexL2 n :=
  (ContinuousLinearMap.proj i).comp
    (ContinuousLinearMap.snd ℂ (ComplexL2 n) (Fin n → ComplexL2 n))

/-- Continuous vector-valued defect `((∂_i u) - g_i)_i`. -/
noncomputable def complexH1GraphDefect (n : Nat) :
    H1ComplexGraphAmbient n →L[ℂ] (Fin n → ScalarDistribution n) :=
  ContinuousLinearMap.pi fun i =>
    (weakPartialCLM i).comp
        ((complexL2ToDistribution n).comp (complexH1ValueProj n)) -
      (complexL2ToDistribution n).comp (complexH1GradProj n i)

/-- Closed distributional H1 graph relation in complex L2 coordinates. -/
noncomputable def H1DistributionalGraphSubmodule (n : Nat) :
    Submodule ℂ (H1ComplexGraphAmbient n) :=
  (complexH1GraphDefect n).ker

/-- Membership means exactly that each stored gradient coordinate is the weak derivative of the
stored value distribution. -/
theorem mem_H1DistributionalGraphSubmodule_iff (n : Nat)
    (x : H1ComplexGraphAmbient n) :
    x ∈ H1DistributionalGraphSubmodule n ↔
      ∀ i : Fin n,
        weakPartial i (complexL2ToDistribution n x.1) =
          complexL2ToDistribution n (x.2 i) := by
  change complexH1GraphDefect n x = 0 ↔ _
  simp [complexH1GraphDefect, complexH1ValueProj, complexH1GradProj,
    weakPartialCLM_apply, sub_eq_zero]

/-- The distributional H1 graph relation is closed because it is the kernel of a continuous defect. -/
theorem isClosed_H1DistributionalGraphSubmodule (n : Nat) :
    IsClosed (H1DistributionalGraphSubmodule n : Set (H1ComplexGraphAmbient n)) := by
  exact (complexH1GraphDefect n).isClosed_ker

/-- Smooth complex H1 graph map `u ↦ (u, (∂_i u)_i)`. -/
noncomputable def smoothComplexH1GraphMap (n : Nat) :
    ComplexSmoothScalar n →ₗ[ℂ] H1ComplexGraphAmbient n where
  toFun u :=
    (schwartzComplexL2 n u,
      fun i => schwartzComplexL2 n (∂_{basisVector i} u))
  map_add' u v := by
    apply Prod.ext
    · simp
    · funext i
      simp [LineDeriv.lineDerivOp_add]
  map_smul' c u := by
    apply Prod.ext
    · simp
    · funext i
      simp [LineDeriv.lineDerivOp_smul]

/-- Smooth Schwartz H1 graph data satisfy the actual distributional derivative equations. -/
theorem smoothComplexH1GraphMap_mem_distributional (n : Nat)
    (u : ComplexSmoothScalar n) :
    smoothComplexH1GraphMap n u ∈ H1DistributionalGraphSubmodule n := by
  rw [mem_H1DistributionalGraphSubmodule_iff]
  intro i
  simp [smoothComplexH1GraphMap, schwartzComplexL2, complexL2ToDistribution,
    weakPartial, MeasureTheory.Lp.toTemperedDistribution_toLp_eq,
    TemperedDistribution.lineDerivOp_toTemperedDistributionCLM_eq]

/-- Smooth complex H1 graph core. -/
noncomputable def ComplexH1SmoothGraphCore (n : Nat) :
    Submodule ℂ (H1ComplexGraphAmbient n) :=
  LinearMap.range (smoothComplexH1GraphMap n)

/-- The smooth H1 graph core lies in the closed distributional graph relation. -/
theorem ComplexH1SmoothGraphCore_le_distributional (n : Nat) :
    ComplexH1SmoothGraphCore n ≤ H1DistributionalGraphSubmodule n := by
  rintro x ⟨u, rfl⟩
  exact smoothComplexH1GraphMap_mem_distributional n u

/-- Therefore the entire smooth H1 graph closure lies in the distributional graph relation. -/
theorem complexH1SmoothGraphClosure_le_distributional (n : Nat) :
    (ComplexH1SmoothGraphCore n).topologicalClosure ≤
      H1DistributionalGraphSubmodule n := by
  exact Submodule.topologicalClosure_minimal (ComplexH1SmoothGraphCore n)
    (ComplexH1SmoothGraphCore_le_distributional n)
    (isClosed_H1DistributionalGraphSubmodule n)

/-- A convergent regularizer upgrades the one-way H1 graph bridge to equality. -/
theorem complexH1SmoothGraphClosure_eq_distributional_of_regularizer
    (n : Nat)
    (R : Nat → H1ComplexGraphAmbient n → H1ComplexGraphAmbient n)
    (hcore : ∀ k x, x ∈ H1DistributionalGraphSubmodule n →
      R k x ∈ ComplexH1SmoothGraphCore n)
    (htendsto : ∀ x, x ∈ H1DistributionalGraphSubmodule n →
      Tendsto (fun k => R k x) atTop (𝓝 x)) :
    (ComplexH1SmoothGraphCore n).topologicalClosure =
      H1DistributionalGraphSubmodule n := by
  change (ComplexH1SmoothGraphCore n).topologicalClosure =
    (complexH1GraphDefect n).ker
  exact submodule_topologicalClosure_eq_ker_of_regularizer
    (ComplexH1SmoothGraphCore n) (complexH1GraphDefect n)
    (ComplexH1SmoothGraphCore_le_distributional n)
    R hcore htendsto

end

end Continuum

end CACEFormal
