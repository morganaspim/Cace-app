import CACEFormal.ContinuumSobolev
import Mathlib.Analysis.Distribution.SchwartzSpace.Basic

namespace CACEFormal

open MeasureTheory
open scoped SchwartzMap ENNReal

namespace Continuum

noncomputable section

/--
Pinned-mathlib bundled model of the Hilbert Sobolev space `H^{s,2}(ℝⁿ)`.
The coordinate is the `L²` representative of the Bessel potential.  The physical
tempered distribution is recovered by the inverse Bessel potential.  This is the
same representation used by the later bundled Mathlib `BesselPotentialSpace`, but
is available on CACE's pinned Mathlib revision.
-/
abbrev Sobolev2Space (n : Nat) (s : ℝ) :=
  Lp ℂ 2 (volume : Measure (EuclideanDomain n))

/-- The underlying `L²` Bessel coordinate. -/
def Sobolev2Space.toLp {n : Nat} {s : ℝ} (u : Sobolev2Space n s) :
    Lp ℂ 2 (volume : Measure (EuclideanDomain n)) :=
  u

/-- Recover the physical tempered distribution from its Bessel coordinate. -/
noncomputable def Sobolev2Space.toDistr {n : Nat} {s : ℝ}
    (u : Sobolev2Space n s) : ScalarDistribution n :=
  TemperedDistribution.besselPotential (EuclideanDomain n) ℂ (-s) (u : ScalarDistribution n)

/-- Every bundled Bessel coordinate realizes an actual Mathlib `MemSobolev s 2` distribution. -/
theorem Sobolev2Space.toDistr_memSobolev {n : Nat} {s : ℝ}
    (u : Sobolev2Space n s) :
    TemperedDistribution.MemSobolev
      (E := EuclideanDomain n) (F := ℂ) s 2 (Sobolev2Space.toDistr (s := s) u) := by
  refine ⟨Sobolev2Space.toLp (s := s) u, ?_⟩
  simp [Sobolev2Space.toDistr, Sobolev2Space.toLp]

/-- Conversely, every Mathlib `MemSobolev s 2` distribution has a bundled Bessel coordinate. -/
theorem exists_sobolev2_of_memSobolev {n : Nat} {s : ℝ}
    {f : ScalarDistribution n}
    (hf : TemperedDistribution.MemSobolev
      (E := EuclideanDomain n) (F := ℂ) s 2 f) :
    ∃ u : Sobolev2Space n s, Sobolev2Space.toDistr (s := s) u = f := by
  rcases hf with ⟨u, hu⟩
  refine ⟨u, ?_⟩
  exact (TemperedDistribution.besselPotential_neg_apply_eq_iff
    (E := EuclideanDomain n) (F := ℂ) s (u : ScalarDistribution n) f).2 hu

/-- The Bessel coordinate representation is injective. -/
theorem Sobolev2Space.toDistr_injective {n : Nat} {s : ℝ} :
    Function.Injective (@Sobolev2Space.toDistr n s) := by
  intro u v huv
  apply_fun TemperedDistribution.besselPotential (EuclideanDomain n) ℂ s at huv
  have h : (u : ScalarDistribution n) = (v : ScalarDistribution n) := by
    simpa [Sobolev2Space.toDistr] using huv
  exact (LinearMap.ker_eq_bot.mp
    (Lp.ker_toTemperedDistributionCLM_eq_bot
      (F := ℂ) (μ := (volume : Measure (EuclideanDomain n))) (p := 2))) h

/-- The subtype of tempered distributions satisfying Mathlib's Sobolev predicate. -/
abbrev MemSobolev2Distribution (n : Nat) (s : ℝ) :=
  {f : ScalarDistribution n // TemperedDistribution.MemSobolev
    (E := EuclideanDomain n) (F := ℂ) s 2 f}

/--
The bundled Bessel-coordinate model is equivalent, as a type, to the actual
`MemSobolev s 2` subtype of tempered distributions.  This packages the two bridge
theorems above into a single reusable representation theorem.
-/
noncomputable def sobolev2EquivMemSobolev (n : Nat) (s : ℝ) :
    Sobolev2Space n s ≃ MemSobolev2Distribution n s :=
  Equiv.ofBijective
    (fun u => ⟨Sobolev2Space.toDistr (s := s) u, Sobolev2Space.toDistr_memSobolev (s := s) u⟩)
    ⟨
      (fun _ _ h => Sobolev2Space.toDistr_injective (Subtype.ext_iff.mp h)),
      (fun f => by
        rcases exists_sobolev2_of_memSobolev f.property with ⟨u, hu⟩
        exact ⟨u, Subtype.ext hu⟩)
    ⟩

/-- H¹ in the bundled pinned model. -/
abbrev BundledH1 (n : Nat) := Sobolev2Space n 1

/-- L² in the bundled pinned model. -/
abbrev BundledL2 (n : Nat) := Sobolev2Space n 0

/-- Schwartz functions mapped to Bessel coordinates.  The target is viewed as a real normed space. -/
noncomputable def schwartzSobolev2Coordinates (n : Nat) (s : ℝ) :
    𝓢(EuclideanDomain n, ℂ) →L[ℝ] Sobolev2Space n s :=
  SchwartzMap.toLpCLM ℝ ℂ 2 volume

/--
Schwartz Bessel coordinates are dense in every bundled `H^{s,2}` space.
This is a genuine density theorem inherited from Mathlib's Schwartz-density theorem in `L²`.
-/
theorem denseRange_schwartzSobolev2Coordinates (n : Nat) (s : ℝ) :
    DenseRange (schwartzSobolev2Coordinates n s) := by
  simpa [schwartzSobolev2Coordinates, Sobolev2Space] using
    (SchwartzMap.denseRange_toLpCLM
      (E := EuclideanDomain n) (F := ℂ) (p := (2 : ℝ≥0∞))
      (μ := (volume : Measure (EuclideanDomain n))) ENNReal.ofNat_ne_top)

/-- In particular, Schwartz Bessel coordinates are dense in bundled H¹. -/
theorem denseRange_schwartzH1 (n : Nat) :
    DenseRange (schwartzSobolev2Coordinates n 1) :=
  denseRange_schwartzSobolev2Coordinates n 1

end

end Continuum

end CACEFormal
