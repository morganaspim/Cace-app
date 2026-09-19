import Mathlib

namespace CACEFormal

/-!
# Runtime approximation boundary

Exact rational and real-number theorems must not silently identify machine
floating-point output with an exact mathematical value.  Approximate runtimes
instead cross into the proof layer through an explicit certificate containing:

* the runtime value;
* a mathematical decoder into `ℝ`;
* the exact specification value;
* a nonnegative error radius;
* a proof that the decoded runtime value is within that radius.

This module is intentionally representation-agnostic.  A future Float, GPU, or
external-kernel adapter must provide its own decoder and rounding/error proof.
No raw approximate value is promoted to exact equality here.
-/

namespace RuntimeApproximation

/-- Closed real interval represented by center and nonnegative radius. -/
structure Interval where
  center : ℝ
  radius : ℝ
  radius_nonneg : 0 ≤ radius

def Interval.lower (I : Interval) : ℝ :=
  I.center - I.radius

def Interval.upper (I : Interval) : ℝ :=
  I.center + I.radius

def Interval.Contains (I : Interval) (x : ℝ) : Prop :=
  I.lower ≤ x ∧ x ≤ I.upper

/-- Certificate connecting one runtime representation to one exact real
specification value. -/
structure CertifiedApproximation (α : Type*) (decode : α → ℝ) where
  runtime : α
  exact : ℝ
  radius : ℝ
  radius_nonneg : 0 ≤ radius
  error_le : |decode runtime - exact| ≤ radius

namespace CertifiedApproximation

def interval {α : Type*} {decode : α → ℝ}
    (c : CertifiedApproximation α decode) : Interval :=
  ⟨decode c.runtime, c.radius, c.radius_nonneg⟩

/-- The exact specification value is guaranteed to lie inside the runtime
value's certified error interval. -/
theorem exact_mem_interval {α : Type*} {decode : α → ℝ}
    (c : CertifiedApproximation α decode) :
    c.interval.Contains c.exact := by
  constructor
  · have h := (abs_le.mp c.error_le).2
    dsimp [interval, Interval.Contains, Interval.lower]
    linarith
  · have h := (abs_le.mp c.error_le).1
    dsimp [interval, Interval.Contains, Interval.upper]
    linarith

/-- Zero certified radius upgrades approximation to exact decoded equality. -/
theorem decode_eq_exact_of_radius_zero {α : Type*} {decode : α → ℝ}
    (c : CertifiedApproximation α decode) (hzero : c.radius = 0) :
    decode c.runtime = c.exact := by
  have h := c.error_le
  rw [hzero] at h
  exact sub_eq_zero.mp (abs_eq_zero.mp (le_antisymm h (abs_nonneg _)))

/-- Symmetric form of the certified error bound. -/
theorem exact_error_le {α : Type*} {decode : α → ℝ}
    (c : CertifiedApproximation α decode) :
    |c.exact - decode c.runtime| ≤ c.radius := by
  simpa [abs_sub_comm] using c.error_le

end CertifiedApproximation

/-- Componentwise certificate for a two-dimensional runtime point. -/
structure CertifiedPointApproximation
    (α : Type*) (decodeX decodeY : α → ℝ) where
  runtime : α
  exactX : ℝ
  exactY : ℝ
  radiusX : ℝ
  radiusY : ℝ
  radiusX_nonneg : 0 ≤ radiusX
  radiusY_nonneg : 0 ≤ radiusY
  errorX_le : |decodeX runtime - exactX| ≤ radiusX
  errorY_le : |decodeY runtime - exactY| ≤ radiusY

/-- A runtime backend is admissible for an exact scalar specification only by
producing a `CertifiedApproximation`; this alias makes that boundary explicit
in APIs without choosing a particular machine representation. -/
abbrev ExactBoundary (α : Type*) (decode : α → ℝ) :=
  CertifiedApproximation α decode

end RuntimeApproximation

end CACEFormal
