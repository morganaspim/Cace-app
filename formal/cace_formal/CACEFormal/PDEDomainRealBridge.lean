import CACEFormal.PDEDomainBridge
import Mathlib.Algebra.Module.Submodule.RestrictScalars
import Mathlib.Topology.Algebra.Module.ContinuousLinearMap.PiProd

namespace CACEFormal

open Set Finset MeasureTheory Filter
open scoped BigOperators LineDeriv SchwartzMap

namespace Continuum

noncomputable section

/-!
# v3.29 real graph-closure to distributional H(div) bridge

The v3.28 closed graph model is real-valued, while the tempered-distribution Sobolev interface is
complex-valued.  This file makes that scalar change explicit.  No real/complex identification is
left implicit: real L² coordinates are mapped through `Complex.ofRealCLM`, smooth Schwartz fields
are postcomposed with the same embedding, and the resulting map is shown compatible with weak
coordinate differentiation on the smooth core.
-/

/-- Canonical real-linear complexification of the whole-space real L² model. -/
noncomputable def realL2ToComplexL2 (n : Nat) :
    RealL2 n →L[ℝ] ComplexL2 n :=
  Complex.ofRealCLM.compLpL 2 volume

/-- Pointwise complexification of a real Schwartz field. -/
noncomputable def realSchwartzToComplex (n : Nat) :
    SmoothScalar n →L[ℝ] ComplexSmoothScalar n :=
  SchwartzMap.postcompCLM Complex.ofRealCLM

/-- L² complexification agrees with pointwise complexification on Schwartz fields. -/
theorem realL2ToComplexL2_schwartz (n : Nat) (f : SmoothScalar n) :
    realL2ToComplexL2 n (schwartzRealL2 n f) =
      schwartzComplexL2 n (realSchwartzToComplex n f) := by
  apply MeasureTheory.Lp.ext
  have hcomp :
      realL2ToComplexL2 n (schwartzRealL2 n f) =ᵐ[volume]
        fun x => Complex.ofRealCLM ((schwartzRealL2 n f) x) := by
    simpa [realL2ToComplexL2] using
      (ContinuousLinearMap.coeFn_compLpL Complex.ofRealCLM (schwartzRealL2 n f))
  have hreal :
      (schwartzRealL2 n f : EuclideanDomain n → ℝ) =ᵐ[volume] f := by
    simpa [schwartzRealL2] using f.coeFn_toLp 2 volume
  have hcomplex :
      (schwartzComplexL2 n (realSchwartzToComplex n f) : EuclideanDomain n → ℂ) =ᵐ[volume]
        realSchwartzToComplex n f := by
    simpa [schwartzComplexL2] using (realSchwartzToComplex n f).coeFn_toLp 2 volume
  filter_upwards [hcomp, hreal, hcomplex] with x hx hfx hcx
  rw [hx, hfx, hcx]
  rfl

/-- Real-to-complex postcomposition commutes with Schwartz directional derivatives. -/
theorem realSchwartzToComplex_lineDeriv (n : Nat) (i : Fin n) (f : SmoothScalar n) :
    ∂_{basisVector i} (realSchwartzToComplex n f) =
      realSchwartzToComplex n (∂_{basisVector i} f) := by
  ext x
  simp only [SchwartzMap.lineDerivOp_apply_eq_fderiv]
  change
    fderiv ℝ (fun y => Complex.ofRealCLM (f y)) x (basisVector i) =
      Complex.ofRealCLM (fderiv ℝ f x (basisVector i))
  have hcomp :
      fderiv ℝ (fun y => Complex.ofRealCLM (f y)) x =
        Complex.ofRealCLM.comp (fderiv ℝ f x) := by
    simpa [Function.comp_def] using
      (fderiv_comp x Complex.ofRealCLM.differentiableAt f.differentiableAt)
  rw [hcomp]
  rfl

/-- Complexify every component of a real smooth vector field. -/
noncomputable def realSmoothVectorToComplex {n : Nat}
    (q : SmoothVector n) : ComplexSmoothVector n :=
  fun i => realSchwartzToComplex n (q i)

/-- Canonical real-linear complexification of H(div) graph coordinates. -/
noncomputable def realHDivGraphToComplex (n : Nat) :
    HDivGraphAmbient n →L[ℝ] HDivComplexGraphAmbient n :=
  ContinuousLinearMap.prod
    (ContinuousLinearMap.pi fun i =>
      (realL2ToComplexL2 n).comp (hdivFieldProj n i))
    ((realL2ToComplexL2 n).comp (hdivDivProj n))

/-- The real and complex smooth H(div) graph maps commute with canonical complexification. -/
theorem realHDivGraphToComplex_smooth (n : Nat) (q : SmoothVector n) :
    realHDivGraphToComplex n (smoothHDivGraphMap n q) =
      smoothComplexHDivGraphMap n (realSmoothVectorToComplex q) := by
  apply Prod.ext
  · funext i
    simp [realHDivGraphToComplex, smoothHDivGraphMap, smoothComplexHDivGraphMap,
      realSmoothVectorToComplex, hdivFieldProj, realL2ToComplexL2_schwartz]
  · simp [realHDivGraphToComplex, smoothHDivGraphMap, smoothComplexHDivGraphMap,
      realSmoothVectorToComplex, hdivDivProj, realL2ToComplexL2_schwartz,
      realSchwartzToComplex_lineDeriv, map_sum]

/-- Every real smooth H(div) graph datum complexifies to the closed distributional graph. -/
theorem realSmoothHDivGraph_mem_distributional (n : Nat) (q : SmoothVector n) :
    realHDivGraphToComplex n (smoothHDivGraphMap n q) ∈
      HDivDistributionalGraphSubmodule n := by
  rw [realHDivGraphToComplex_smooth]
  exact smoothComplexHDivGraphMap_mem_distributional n (realSmoothVectorToComplex q)

/-- Pull the complex distributional H(div) relation back to the real v3.28 graph ambient space. -/
noncomputable def RealHDivDistributionalPreimage (n : Nat) :
    Submodule ℝ (HDivGraphAmbient n) :=
  ((HDivDistributionalGraphSubmodule n).restrictScalars ℝ).comap
    (realHDivGraphToComplex n).toLinearMap

@[simp]
theorem mem_RealHDivDistributionalPreimage_iff (n : Nat) (x : HDivGraphAmbient n) :
    x ∈ RealHDivDistributionalPreimage n ↔
      realHDivGraphToComplex n x ∈ HDivDistributionalGraphSubmodule n := by
  rfl

/-- The pulled-back distributional graph relation is closed in real graph coordinates. -/
theorem isClosed_RealHDivDistributionalPreimage (n : Nat) :
    IsClosed (RealHDivDistributionalPreimage n : Set (HDivGraphAmbient n)) := by
  change IsClosed ((realHDivGraphToComplex n) ⁻¹'
    (HDivDistributionalGraphSubmodule n : Set (HDivComplexGraphAmbient n)))
  exact (isClosed_HDivDistributionalGraphSubmodule n).preimage
    (realHDivGraphToComplex n).continuous

/-- The real smooth graph core lies in the genuine distributional H(div) relation after complexification. -/
theorem HDivSmoothGraphCore_le_RealHDivDistributionalPreimage (n : Nat) :
    HDivSmoothGraphCore n ≤ RealHDivDistributionalPreimage n := by
  rintro x ⟨q, rfl⟩
  exact realSmoothHDivGraph_mem_distributional n q

/--
The whole v3.28 real H(div) graph closure complexifies into the closed distributional graph relation.
This is the explicit real-v3.28 → complex-distributional bridge.
-/
theorem HDivGraphClosedSpace_le_RealHDivDistributionalPreimage (n : Nat) :
    (HDivSmoothGraphCore n).topologicalClosure ≤ RealHDivDistributionalPreimage n := by
  exact Submodule.topologicalClosure_minimal (HDivSmoothGraphCore n)
    (HDivSmoothGraphCore_le_RealHDivDistributionalPreimage n)
    (isClosed_RealHDivDistributionalPreimage n)

/-- Every field in the actual v3.28 real graph closure has a genuine distributional H(div) complex image. -/
theorem HDivGraphClosedSpace.toInHDiv (n : Nat) (q : HDivGraphClosedSpace n) :
    InHDiv (complexGraphFieldDistribution (realHDivGraphToComplex n q.1)) := by
  apply inHDiv_of_mem_distributionalGraph n
  exact (HDivGraphClosedSpace_le_RealHDivDistributionalPreimage n) q.2

end

end Continuum

end CACEFormal
