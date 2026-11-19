/- Core-only predicates and finite integer grades. No Mathlib dependency.
   Each theorem states exactly which witness and which dynamics are preserved.
   This file does not claim novelty or formal correctness of a Python executor. -/
namespace MerlinTemporal

universe u v w

def Joint {X : Type u} {I : Type v}
    (accept : I -> X -> Prop) (selected : I -> Prop) : Prop :=
  Exists fun x => forall i, selected i -> accept i x

theorem joint_restrict {X : Type u} {I : Type v}
    (accept : I -> X -> Prop) (small large : I -> Prop)
    (hsub : forall i, small i -> large i) :
    Joint accept large -> Joint accept small := by
  intro h
  cases h with
  | intro x hx =>
    exact Exists.intro x (fun i hi => hx i (hsub i hi))

theorem witness_map {X : Type u} {Y : Type w} {I : Type v}
    (a : I -> X -> Prop) (b : I -> Y -> Prop) (selected : I -> Prop)
    (f : X -> Y) (preserves : forall i x, a i x -> b i (f x)) :
    Joint a selected -> Joint b selected := by
  intro h
  cases h with
  | intro x hx =>
    exact Exists.intro (f x) (fun i hi => preserves i x (hx i hi))

theorem surjective_pullback {X : Type u} {Y : Type w} {I : Type v}
    (a : I -> Y -> Prop) (selected : I -> Prop) (f : X -> Y)
    (onto : forall y, Exists fun x => f x = y) :
    Joint (fun i x => a i (f x)) selected <-> Joint a selected := by
  constructor
  . intro h
    cases h with
    | intro x hx => exact Exists.intro (f x) hx
  . intro h
    cases h with
    | intro y hy =>
      cases onto y with
      | intro x hxy =>
        apply Exists.intro x
        intro i hi
        rw [hxy]
        exact hy i hi

theorem pointwise_maps_compose {X Y Z I : Type}
    (a : I -> X -> Prop) (b : I -> Y -> Prop) (c : I -> Z -> Prop)
    (f : X -> Y) (g : Y -> Z)
    (hf : forall i x, a i x -> b i (f x))
    (hg : forall i y, b i y -> c i (g y)) :
    forall i x, a i x -> c i (g (f x)) :=
  fun i x hx => hg i (f x) (hf i x hx)

def TrajectoryJoint {X I T : Type}
    (flow : T -> X -> X) (accept : T -> I -> X -> Prop)
    (selected : T -> I -> Prop) : Prop :=
  Exists fun x0 => forall t i, selected t i -> accept t i (flow t x0)

theorem trajectory_implies_separate_time_witnesses {X I T : Type}
    (flow : T -> X -> X) (accept : T -> I -> X -> Prop)
    (selected : T -> I -> Prop) :
    TrajectoryJoint flow accept selected ->
      forall t, Exists fun x0 => forall i, selected t i -> accept t i (flow t x0) := by
  intro h t
  cases h with
  | intro x hx => exact Exists.intro x (hx t)

theorem trajectory_surjective_transport {X Y I T : Type}
    (source : T -> X -> X) (target : T -> Y -> Y)
    (accept : T -> I -> Y -> Prop) (selected : T -> I -> Prop)
    (f : X -> Y) (onto : forall y, Exists fun x => f x = y)
    (commutes : forall t x, f (source t x) = target t (f x)) :
    TrajectoryJoint source (fun t i x => accept t i (f x)) selected <->
    TrajectoryJoint target accept selected := by
  constructor
  . intro h
    cases h with
    | intro x hx =>
      apply Exists.intro (f x)
      intro t i hi
      have h := hx t i hi
      change accept t i (f (source t x)) at h
      rw [commutes t x] at h
      exact h
  . intro h
    cases h with
    | intro y hy =>
      cases onto y with
      | intro x hxy =>
        apply Exists.intro x
        intro t i hi
        have h := hy t i hi
        change accept t i (f (source t x))
        rw [commutes t x, hxy]
        exact h

/-- A common-state requirement is strictly stronger than individual feasibility. -/
theorem independent_is_not_joint :
    And (forall t : Bool, Exists fun x : Bool => x = t)
      (Not (Exists fun x : Bool => forall t : Bool, x = t)) := by
  constructor
  . intro t
    exact Exists.intro t rfl
  . intro h
    cases h with
    | intro x hx =>
      have bad : false = true := (hx false).symm.trans (hx true)
      cases bad

/-- Uncertainty budgets are natural-number fixed-point grade units. -/
def SlackJoint {X I : Type} (grade : I -> X -> Nat)
    (selected : I -> Prop) (threshold slack : Nat) : Prop :=
  Exists fun x => forall i, selected i -> threshold <= grade i x + slack

theorem matched_slack_transfer {X Y I : Type}
    (source : I -> X -> Nat) (target : I -> Y -> Nat)
    (selected : I -> Prop) (threshold old extra : Nat)
    (matchState : forall x, Exists fun y => forall i,
       selected i -> source i x <= target i y + extra) :
    SlackJoint source selected threshold old ->
    SlackJoint target selected threshold (extra + old) := by
  intro h
  cases h with
  | intro x hx =>
    cases matchState x with
    | intro y hy =>
      apply Exists.intro y
      intro i hi
      have upper := Nat.add_le_add_right (hy i hi) old
      have result := Nat.le_trans (hx i hi) upper
      rw [Nat.add_assoc] at result
      exact result

/-- Six phases and three times; four integer units mean membership one. -/
def cycleGrade (x : Fin 6) (t : Fin 3) : Nat :=
  match (x.val + 2 * t.val) % 6 with
  | 0 => 4
  | 1 => 3
  | 2 => 1
  | 3 => 0
  | 4 => 1
  | _ => 3

theorem all_grades_bounded :
    forall x : Fin 6, forall t : Fin 3, cycleGrade x t <= 4 := by decide

theorem each_time_attains_one :
    forall t : Fin 3, Exists fun x : Fin 6 => cycleGrade x t = 4 := by decide

theorem each_pair_attains_three_quarters :
    forall s t : Fin 3, Not (s = t) -> Exists fun x : Fin 6 =>
      And (3 <= cycleGrade x s) (3 <= cycleGrade x t) := by decide

theorem each_pair_upper_three_quarters :
    forall s t : Fin 3, Not (s = t) -> forall x : Fin 6,
      Or (cycleGrade x s <= 3) (cycleGrade x t <= 3) := by decide

theorem joint_upper_one_quarter :
    forall x : Fin 6, Exists fun t : Fin 3 => cycleGrade x t <= 1 := by decide

theorem joint_attains_one_quarter :
    Exists fun x : Fin 6 => forall t : Fin 3, 1 <= cycleGrade x t := by decide

theorem no_joint_half :
    Not (Exists fun x : Fin 6 => forall t : Fin 3, 2 <= cycleGrade x t) := by decide

theorem row_sum_six :
    forall x : Fin 6,
      cycleGrade x 0 + cycleGrade x 1 + cycleGrade x 2 = 6 := by decide

theorem equal_mixture_certificate :
    forall t : Fin 3,
      cycleGrade 0 t + cycleGrade 2 t + cycleGrade 4 t = 6 := by decide

end MerlinTemporal
#print axioms MerlinTemporal.joint_restrict
#print axioms MerlinTemporal.witness_map
#print axioms MerlinTemporal.surjective_pullback
#print axioms MerlinTemporal.pointwise_maps_compose
#print axioms MerlinTemporal.trajectory_implies_separate_time_witnesses
#print axioms MerlinTemporal.trajectory_surjective_transport
#print axioms MerlinTemporal.independent_is_not_joint
#print axioms MerlinTemporal.matched_slack_transfer
#print axioms MerlinTemporal.all_grades_bounded
#print axioms MerlinTemporal.each_time_attains_one
#print axioms MerlinTemporal.each_pair_attains_three_quarters
#print axioms MerlinTemporal.each_pair_upper_three_quarters
#print axioms MerlinTemporal.joint_upper_one_quarter
#print axioms MerlinTemporal.joint_attains_one_quarter
#print axioms MerlinTemporal.no_joint_half
#print axioms MerlinTemporal.row_sum_six
#print axioms MerlinTemporal.equal_mixture_certificate
