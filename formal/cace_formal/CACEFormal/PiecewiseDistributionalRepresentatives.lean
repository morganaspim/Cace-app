import CACEFormal.DistributionalGraphRepresentatives
import CACEFormal.H1GraphConverse
import CACEFormal.PiecewiseInterfaceCancellation

namespace CACEFormal

namespace Continuum

noncomputable section

/-!
# Piecewise interface cancellation to distributional graph representatives

This module records the exact endpoint after the geometric/measure-theoretic
piecewise integration-by-parts construction has produced tempered
distributions and proved their global weak equations.

It deliberately does not manufacture a distribution from finite coefficient
data.  That construction must prove measurability/L² integrability and the
cellwise integration-by-parts formula.  Once those facts and interface
cancellation yield the graph equations below, the existing CACE representative
machinery supplies InH1/InHDiv and canonical L² graph coordinates.
-/

/--
A scalar distribution with an actual L² value representative and actual L²
weak-derivative representatives is in H¹ once the global weak equations have
been obtained by cell assembly and interface cancellation.
-/
theorem inH1_of_piecewise_interface_cancelled_graph
    {n : Nat}
    (u : ComplexL2 n)
    (grad : Fin n → ComplexL2 n)
    (hweak : ∀ i : Fin n,
      weakPartial i (complexL2ToDistribution n u) =
        complexL2ToDistribution n (grad i)) :
    InH1 (complexL2ToDistribution n u) := by
  let x : H1ComplexGraphAmbient n := (u, grad)
  have hx : x ∈ H1DistributionalGraphSubmodule n := by
    rw [mem_H1DistributionalGraphSubmodule_iff]
    exact hweak
  exact inH1_of_mem_H1DistributionalGraphSubmodule n x hx

/--
The same scalar hypotheses feed directly into the existing chosen L²
representative machinery.  The returned representative satisfies the closed
distributional H¹ graph relation and represents the same value distribution.
-/
theorem piecewise_interface_cancelled_has_H1_representative
    {n : Nat}
    (u : ComplexL2 n)
    (grad : Fin n → ComplexL2 n)
    (hweak : ∀ i : Fin n,
      weakPartial i (complexL2ToDistribution n u) =
        complexL2ToDistribution n (grad i)) :
    ∃ x : H1ComplexGraphAmbient n,
      x ∈ H1DistributionalGraphSubmodule n ∧
      complexL2ToDistribution n x.1 = complexL2ToDistribution n u := by
  exact inH1_has_distributionalGraphRepresentative
    (complexL2ToDistribution n u)
    (inH1_of_piecewise_interface_cancelled_graph u grad hweak)

/--
A vector L² field with an L² divergence representative is in H(div) once
cellwise integration by parts plus RT0 normal-interface cancellation has
established the global distributional divergence equation.
-/
theorem inHDiv_of_piecewise_normal_interface_cancelled_graph
    {n : Nat}
    (q : Fin n → ComplexL2 n)
    (divQ : ComplexL2 n)
    (hdiv :
      distributionalDivergence
          (fun i => complexL2ToDistribution n (q i)) =
        complexL2ToDistribution n divQ) :
    InHDiv (fun i => complexL2ToDistribution n (q i)) := by
  let x : HDivComplexGraphAmbient n := (q, divQ)
  have hx : x ∈ HDivDistributionalGraphSubmodule n := by
    rw [mem_HDivDistributionalGraphSubmodule_iff]
    exact hdiv
  simpa [x, complexGraphFieldDistribution] using
    inHDiv_of_mem_distributionalGraph n x hx

/--
The H(div) endpoint also connects to the existing canonical chosen L² graph
representative without duplicating the representation theorem.
-/
theorem piecewise_normal_interface_cancelled_has_HDiv_representative
    {n : Nat}
    (q : Fin n → ComplexL2 n)
    (divQ : ComplexL2 n)
    (hdiv :
      distributionalDivergence
          (fun i => complexL2ToDistribution n (q i)) =
        complexL2ToDistribution n divQ) :
    ∃ x : HDivComplexGraphAmbient n,
      x ∈ HDivDistributionalGraphSubmodule n ∧
      complexGraphFieldDistribution x =
        (fun i => complexL2ToDistribution n (q i)) := by
  exact (inHDiv_iff_exists_distributionalGraphRepresentative
    (fun i => complexL2ToDistribution n (q i))).mp
      (inHDiv_of_piecewise_normal_interface_cancelled_graph q divQ hdiv)

end

end Continuum

end CACEFormal
