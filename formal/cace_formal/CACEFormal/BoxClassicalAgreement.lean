import CACEFormal.BoxGraphGreenPairing
import Mathlib.MeasureTheory.Function.L2Space

namespace CACEFormal

open Set Finset MeasureTheory Filter
open scoped BigOperators InnerProductSpace LineDeriv SchwartzMap

namespace Continuum

noncomputable section

/-!
# Classical interpretation of the bounded-box graph pairing

The box graph spaces are built from `L²` for `volume.restrict (Icc a b)`.  The lemmas here expose
that Hilbert pairing as the ordinary box integral used by the classical Green theorem.  This is the
non-definitional bridge needed before identifying the closure-level functional trace with signed
face flux.
-/

/-- The restricted-box L² inner product of two Schwartz fields is their classical product integral. -/
theorem boxSchwartzL2_inner_eq_setIntegral_mul {n : Nat}
    (a b : BoxPoint n) (f g : BoxSmoothScalar n) :
    inner ℝ (boxSchwartzL2 a b f) (boxSchwartzL2 a b g) =
      ∫ x in Icc a b, f x * g x := by
  rw [MeasureTheory.L2.inner_def]
  apply integral_congr_ae
  have hf :
      (boxSchwartzL2 a b f : BoxPoint n → ℝ) =ᵐ[boxVolume a b] f := by
    simpa [boxSchwartzL2] using f.coeFn_toLp 2 (boxVolume a b)
  have hg :
      (boxSchwartzL2 a b g : BoxPoint n → ℝ) =ᵐ[boxVolume a b] g := by
    simpa [boxSchwartzL2] using g.coeFn_toLp 2 (boxVolume a b)
  filter_upwards [hf, hg] with x hfx hgx
  simp [hfx, hgx, RCLike.inner_apply, mul_comm]

/-- Smooth divergence as a Schwartz scalar field. -/
noncomputable def smoothBoxDivergence {n : Nat} (q : BoxSmoothVector n) :
    BoxSmoothScalar n :=
  ∑ i : Fin (n + 1), ∂_{boxBasisVector i} (q i)

/-- The divergence coordinate in the smooth box graph is exactly the L² image of smooth divergence. -/
theorem smoothBoxHDivGraphMap_divergence {n : Nat}
    (a b : BoxPoint n) (q : BoxSmoothVector n) :
    (smoothBoxHDivGraphMap a b q).2 =
      boxSchwartzL2 a b (smoothBoxDivergence q) := by
  simp [smoothBoxHDivGraphMap, smoothBoxDivergence]

/-- The field coordinate in the smooth H(div) box graph is the corresponding restricted L² field. -/
theorem smoothBoxHDivGraphMap_field {n : Nat}
    (a b : BoxPoint n) (q : BoxSmoothVector n) (i : Fin (n + 1)) :
    (smoothBoxHDivGraphMap a b q).1 i = boxSchwartzL2 a b (q i) := by
  rfl

/-- The value coordinate in the smooth H¹ box graph is the restricted L² scalar field. -/
theorem smoothBoxH1GraphMap_value {n : Nat}
    (a b : BoxPoint n) (v : BoxSmoothScalar n) :
    (smoothBoxH1GraphMap a b v).1 = boxSchwartzL2 a b v := by
  rfl

/-- The gradient coordinate in the smooth H¹ box graph is the restricted L² weak/classical derivative. -/
theorem smoothBoxH1GraphMap_gradient {n : Nat}
    (a b : BoxPoint n) (v : BoxSmoothScalar n) (i : Fin (n + 1)) :
    (smoothBoxH1GraphMap a b v).2 i =
      boxSchwartzL2 a b (∂_{boxBasisVector i} v) := by
  rfl

/-- The divergence/value part of the graph Green pairing has its classical box-integral form. -/
theorem boxSmooth_div_value_pairing_eq_integral {n : Nat}
    (a b : BoxPoint n) (q : BoxSmoothVector n) (v : BoxSmoothScalar n) :
    inner ℝ (smoothBoxHDivGraphMap a b q).2 (smoothBoxH1GraphMap a b v).1 =
      ∫ x in Icc a b, smoothBoxDivergence q x * v x := by
  rw [smoothBoxHDivGraphMap_divergence, smoothBoxH1GraphMap_value]
  exact boxSchwartzL2_inner_eq_setIntegral_mul a b (smoothBoxDivergence q) v

/-- Each field/gradient coordinate pairing has its classical box-integral form. -/
theorem boxSmooth_field_gradient_pairing_eq_integral {n : Nat}
    (a b : BoxPoint n) (q : BoxSmoothVector n) (v : BoxSmoothScalar n)
    (i : Fin (n + 1)) :
    inner ℝ ((smoothBoxHDivGraphMap a b q).1 i)
      ((smoothBoxH1GraphMap a b v).2 i) =
      ∫ x in Icc a b, q i x * (∂_{boxBasisVector i} v) x := by
  rw [smoothBoxHDivGraphMap_field, smoothBoxH1GraphMap_gradient]
  exact boxSchwartzL2_inner_eq_setIntegral_mul a b (q i) (∂_{boxBasisVector i} v)

/-- Pointwise vector field represented by a smooth vector graph datum. -/
def smoothBoxVectorFunction {n : Nat} (q : BoxSmoothVector n) :
    BoxPoint n → BoxPoint n :=
  fun x i => q i x

/-- Pointwise gradient represented by a smooth scalar graph datum. -/
def smoothBoxGradientFunction {n : Nat} (v : BoxSmoothScalar n) :
    BoxPoint n → BoxPoint n :=
  fun x i => (∂_{boxBasisVector i} v) x

/-- Classical sum-of-volume-pairings corresponding exactly to the smooth graph coordinates. -/
noncomputable def smoothBoxGraphVolume {n : Nat}
    (a b : BoxPoint n) (q : BoxSmoothVector n) (v : BoxSmoothScalar n) : ℝ :=
  (∑ i : Fin (n + 1),
      ∫ x in Icc a b, q i x * (∂_{boxBasisVector i} v) x) +
    ∫ x in Icc a b, smoothBoxDivergence q x * v x

/-- The ambient graph Green pairing on smooth graph data is the classical sum of box integrals. -/
theorem ambientBoxGraphGreenPairing_smooth_eq_graphVolume {n : Nat}
    (a b : BoxPoint n) (q : BoxSmoothVector n) (v : BoxSmoothScalar n) :
    ambientBoxGraphGreenPairing a b
        (smoothBoxHDivGraphMap a b q) (smoothBoxH1GraphMap a b v) =
      smoothBoxGraphVolume a b q v := by
  calc
    ambientBoxGraphGreenPairing a b
        (smoothBoxHDivGraphMap a b q) (smoothBoxH1GraphMap a b v) =
      (∑ i : Fin (n + 1),
        inner ℝ ((smoothBoxHDivGraphMap a b q).1 i)
          ((smoothBoxH1GraphMap a b v).2 i)) +
        inner ℝ (smoothBoxHDivGraphMap a b q).2
          (smoothBoxH1GraphMap a b v).1 :=
      ambientBoxGraphGreenPairing_apply a b _ _
    _ = smoothBoxGraphVolume a b q v := by
      unfold smoothBoxGraphVolume
      congr 1
      · apply Finset.sum_congr rfl
        intro i hi
        exact boxSmooth_field_gradient_pairing_eq_integral a b q v i
      · exact boxSmooth_div_value_pairing_eq_integral a b q v

/-- The graph-volume sum is the integral of the classical Green volume integrand. -/
theorem smoothBoxGraphVolume_eq_greenVolumeIntegral {n : Nat}
    (a b : BoxPoint n) (q : BoxSmoothVector n) (v : BoxSmoothScalar n) :
    smoothBoxGraphVolume a b q v =
      ∫ x in Icc a b,
        smoothGreenVolumeTerm (smoothBoxVectorFunction q) v
          (smoothBoxGradientFunction v) (smoothBoxDivergence q) x := by
  have hfield : ∀ i : Fin (n + 1),
      IntegrableOn (fun x => q i x * (∂_{boxBasisVector i} v) x) (Icc a b) := by
    intro i
    exact ((q i).continuous.mul (∂_{boxBasisVector i} v).continuous).continuousOn
      |>.integrableOn_compact isCompact_Icc
  have hdiv :
      IntegrableOn (fun x => smoothBoxDivergence q x * v x) (Icc a b) := by
    exact ((smoothBoxDivergence q).continuous.mul v.continuous).continuousOn
      |>.integrableOn_compact isCompact_Icc
  have hsum :
      IntegrableOn
        (fun x => ∑ i : Fin (n + 1), q i x * (∂_{boxBasisVector i} v) x)
        (Icc a b) := by
    exact integrable_finsetSum _ (fun i _ => hfield i)
  have hsumIntegral :
      (∫ x in Icc a b,
        ∑ i : Fin (n + 1), q i x * (∂_{boxBasisVector i} v) x) =
      ∑ i : Fin (n + 1),
        ∫ x in Icc a b, q i x * (∂_{boxBasisVector i} v) x := by
    simpa using
      (integral_finsetSum
        (μ := (volume : Measure (BoxPoint n)).restrict (Icc a b))
        Finset.univ (fun i _ => hfield i))
  unfold smoothBoxGraphVolume
  rw [← hsumIntegral]
  rw [← integral_add hsum hdiv]
  rfl

/-- Smooth H(div) graph data embedded into the closed box graph space. -/
noncomputable def smoothBoxHDivClosedPoint {n : Nat}
    (a b : BoxPoint n) (q : BoxSmoothVector n) : BoxHDivGraphClosedSpace a b := by
  refine ⟨smoothBoxHDivGraphMap a b q, ?_⟩
  apply (BoxHDivSmoothGraphCore a b).le_topologicalClosure
  exact ⟨q, rfl⟩

/-- Smooth H¹ graph data embedded into the closed box graph space. -/
noncomputable def smoothBoxH1ClosedPoint {n : Nat}
    (a b : BoxPoint n) (v : BoxSmoothScalar n) : BoxH1GraphClosedSpace a b := by
  refine ⟨smoothBoxH1GraphMap a b v, ?_⟩
  apply (BoxH1SmoothGraphCore a b).le_topologicalClosure
  exact ⟨v, rfl⟩

/-- On embedded smooth graph data, the closure trace reduces to the ambient Green pairing. -/
theorem boxGraphNormalTrace_smoothPoint {n : Nat}
    (a b : BoxPoint n) (q : BoxSmoothVector n) (v : BoxSmoothScalar n) :
    boxGraphNormalTrace a b (smoothBoxHDivClosedPoint a b q)
        (smoothBoxH1ClosedPoint a b v) =
      ambientBoxGraphGreenPairing a b
        (smoothBoxHDivGraphMap a b q) (smoothBoxH1GraphMap a b v) := by
  rfl

/--
On smooth box graph data satisfying the hypotheses of the already machine-checked classical Green
theorem, the closure-level functional normal trace is exactly the classical signed face-flux trace.
-/
theorem boxGraphNormalTrace_smooth_eq_classical {n : Nat}
    {a b : BoxPoint n} (hle : a ≤ b)
    (q : BoxSmoothVector n) (v : BoxSmoothScalar n)
    (F' : BoxPoint n → BoxPoint n →L[ℝ] BoxPoint n)
    (s : Set (BoxPoint n)) (hs : s.Countable)
    (Hc : ContinuousOn
      (scalarTimesVector v (smoothBoxVectorFunction q)) (Icc a b))
    (Hd : ∀ x ∈ (Set.pi univ fun i => Ioo (a i) (b i)) \ s,
      HasFDerivAt (scalarTimesVector v (smoothBoxVectorFunction q)) (F' x) x)
    (Hi : IntegrableOn
      (fun x => ∑ i : Fin (n + 1), F' x (Pi.single i (1 : ℝ)) i)
      (Icc a b))
    (hprod : ∀ x,
      (∑ i : Fin (n + 1), F' x (Pi.single i (1 : ℝ)) i) =
        smoothGreenVolumeTerm (smoothBoxVectorFunction q) v
          (smoothBoxGradientFunction v) (smoothBoxDivergence q) x) :
    boxGraphNormalTrace a b (smoothBoxHDivClosedPoint a b q)
        (smoothBoxH1ClosedPoint a b v) =
      smoothBoxNormalTrace a b
        (scalarTimesVector v (smoothBoxVectorFunction q)) := by
  rw [boxGraphNormalTrace_smoothPoint,
    ambientBoxGraphGreenPairing_smooth_eq_graphVolume,
    smoothBoxGraphVolume_eq_greenVolumeIntegral]
  exact (smoothBoxTrace_eq_greenVolume hle
    (smoothBoxVectorFunction q) v (smoothBoxGradientFunction v)
    (smoothBoxDivergence q) F' s hs Hc Hd Hi hprod).symm

/--
Dense-extension uniqueness specialized to the bounded-box graph closure: any continuous bilinear
trace agreeing with `boxGraphNormalTrace` on the two dense smooth graph cores agrees everywhere.
-/
theorem boxGraphNormalTrace_unique_of_denseSmoothAgreement {n : Nat}
    (a b : BoxPoint n)
    (T : BoxHDivGraphClosedSpace a b →L[ℝ]
      BoxH1GraphClosedSpace a b →L[ℝ] ℝ)
    (hcore : ∀ q, q ∈ BoxHDivDenseSmoothCore a b →
      ∀ v, v ∈ BoxH1DenseSmoothCore a b →
        boxGraphNormalTrace a b q v = T q v) :
    boxGraphNormalTrace a b = T := by
  let H : BoundedGreenPairing (BoxH1GraphClosedSpace a b)
      (BoxHDivGraphClosedSpace a b) :=
    { volumePairing := T
      normalTrace := T }
  exact normalTrace_eq_of_classicalCoreAgreement
    (boxGraphBoundedGreenPairing a b) H
    (BoxHDivDenseSmoothCore a b) (BoxH1DenseSmoothCore a b)
    (dense_BoxHDivDenseSmoothCore a b) (dense_BoxH1DenseSmoothCore a b)
    hcore

end

end Continuum

end CACEFormal
