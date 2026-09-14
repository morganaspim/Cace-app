# ADR 0009 — Theorem registry and general 2D contract

CACE v0.7 introduces theorem contracts with explicit statuses: machine-checked, reviewed/assumed,
computationally discharged, and obligation-only. Registration is metadata, not proof.

The reusable v0.7 2D gate is computationally discharged: it matches explicit assumptions and compares
independently certified continuum-error and residual-estimator intervals. It does not establish the
still-open mesh-uniform PDE reliability theorem. The generic theorem remains an exported Lean obligation.
