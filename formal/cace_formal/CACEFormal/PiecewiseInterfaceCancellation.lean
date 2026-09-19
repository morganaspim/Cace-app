import CACEFormal.P1RT0BoxVolumeBridge

namespace CACEFormal

open scoped BigOperators

namespace Continuum

noncomputable section

/-!
# Reusable distributional interface-cancellation criterion

This module separates the finite-partition distributional argument from the
construction of concrete Mathlib L² representatives.
-/

theorem piecewise_weakPartial_of_interface_cancellation
    {Cell Test : Type*} [Fintype Cell]
    {d : Nat}
    (cellWeak : Fin d → Cell → Test → ℝ)
    (bulk interface : Fin d → Test → ℝ)
    (hCellAssembly : ∀ i φ,
      (∑ K, cellWeak i K φ) = bulk i φ + interface i φ)
    (hInterfaceZero : ∀ i φ, interface i φ = 0) :
    ∀ i φ, (∑ K, cellWeak i K φ) = bulk i φ := by
  intro i φ
  rw [hCellAssembly i φ, hInterfaceZero i φ, add_zero]

theorem piecewise_divergence_of_normal_interface_cancellation
    {Cell Test : Type*} [Fintype Cell]
    (cellDiv : Cell → Test → ℝ)
    (bulkDiv interface : Test → ℝ)
    (hCellAssembly : ∀ φ,
      (∑ K, cellDiv K φ) = bulkDiv φ + interface φ)
    (hInterfaceZero : ∀ φ, interface φ = 0) :
    ∀ φ, (∑ K, cellDiv K φ) = bulkDiv φ := by
  intro φ
  rw [hCellAssembly φ, hInterfaceZero φ, add_zero]

theorem weighted_paired_interfaces_sum_zero
    {Face Test : Type*} [Fintype Face]
    (left right : Face → Test → ℝ)
    (hCancel : ∀ F φ, left F φ + right F φ = 0) :
    ∀ φ, (∑ F, (left F φ + right F φ)) = 0 := by
  intro φ
  apply Finset.sum_eq_zero
  intro F _
  exact hCancel F φ


/--
If a scalar trace is single-valued on an interior face and the two oriented
normal coefficients are opposite, then the interface term cancels against an
arbitrary test trace.  No polynomial assumption on the test trace is used.
-/
theorem arbitrary_test_trace_cancel_of_scalar_trace_and_opposite_normal
    {Face Test : Type*}
    (scalarTrace testTrace leftNormal rightNormal : Face → Test → ℝ)
    (hNormal : ∀ F φ, leftNormal F φ + rightNormal F φ = 0) :
    ∀ F φ,
      scalarTrace F φ * testTrace F φ * leftNormal F φ +
        scalarTrace F φ * testTrace F φ * rightNormal F φ = 0 := by
  intro F φ
  rw [← mul_add]
  rw [hNormal F φ, mul_zero]

/--
Equivalent factorization used for the P1 side: if the two cell traces agree,
a common arbitrary test trace may be factored before applying the oriented
normal cancellation.
-/
theorem arbitrary_test_trace_cancel_of_matching_p1_traces
    {Face Test : Type*}
    (leftTrace rightTrace testTrace leftNormal rightNormal : Face → Test → ℝ)
    (hTrace : ∀ F φ, leftTrace F φ = rightTrace F φ)
    (hNormal : ∀ F φ, leftNormal F φ + rightNormal F φ = 0) :
    ∀ F φ,
      leftTrace F φ * testTrace F φ * leftNormal F φ +
        rightTrace F φ * testTrace F φ * rightNormal F φ = 0 := by
  intro F φ
  rw [hTrace F φ]
  exact arbitrary_test_trace_cancel_of_scalar_trace_and_opposite_normal
    rightTrace testTrace leftNormal rightNormal hNormal F φ

/--
Finite assembly of the arbitrary-test-trace cancellation theorem.
-/
theorem arbitrary_test_trace_interface_sum_zero
    {Face Test : Type*} [Fintype Face]
    (leftTrace rightTrace testTrace leftNormal rightNormal : Face → Test → ℝ)
    (hTrace : ∀ F φ, leftTrace F φ = rightTrace F φ)
    (hNormal : ∀ F φ, leftNormal F φ + rightNormal F φ = 0) :
    ∀ φ,
      (∑ F,
        (leftTrace F φ * testTrace F φ * leftNormal F φ +
          rightTrace F φ * testTrace F φ * rightNormal F φ)) = 0 := by
  intro φ
  apply Finset.sum_eq_zero
  intro F _
  exact arbitrary_test_trace_cancel_of_matching_p1_traces
    leftTrace rightTrace testTrace leftNormal rightNormal hTrace hNormal F φ

theorem exact_interface_certificate_sum_zero
    {mesh : MeshCertificate}
    (triangle : Fin mesh.triangleCount → Triangle2)
    (primal : Fin mesh.triangleCount → P1Affine)
    (flux : Fin mesh.triangleCount → RT0Affine)
    (hInterface : P1RT0InterfaceCancellation triangle primal flux) :
    (∑ i : Fin mesh.interiorEdgeCount,
      (P1RT0Element.localFacePairing
          (triangle (mesh.interiorLeftCell i))
          (primal (mesh.interiorLeftCell i))
          (flux (mesh.interiorLeftCell i))
          (mesh.interiorLeftSlot i) +
       P1RT0Element.localFacePairing
          (triangle (mesh.interiorRightCell i))
          (primal (mesh.interiorRightCell i))
          (flux (mesh.interiorRightCell i))
          (mesh.interiorRightSlot i))) = 0 := by
  apply Finset.sum_eq_zero
  intro i _
  exact hInterface.interiorZero i

end

end Continuum

end CACEFormal
