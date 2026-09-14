# CACE Formal

Pinned Lean 4 / mathlib project for CACE theorem-prover evidence.

## Bootstrap

1. Install `elan` using the official Lean installer.
2. `cd formal/cace_formal`
3. `lake update`
4. `lake exe cache get`
5. `lake build`

This repository pins Lean and mathlib to v4.32.1. The current CACE build runtime had no Lean/elan/lake and could not resolve the elan download host, so Lean proof execution is recorded as `NOT_RUN`, never as a pass.

## Evidence boundary

`CACE-Prager-Synge-Exact-Kernel` independently verifies the run-specific rational
orthogonality, hypercircle identity, equilibrium constraints, and interior-face sign
cancellation. This is a second verifier, not a substitute for Lean.

Run `scripts/check_formal.sh` to cross the external theorem-prover boundary. The script
returns exit code 77 when Lean/lake are unavailable, and CACE must record that state as
`NOT_RUN` rather than `PASS`.

The current remaining source-level bridge is the derivation of mesh orthogonality from
finite-element Green identities, normal-flux continuity/equilibrium, and boundary
admissibility. See `FORMAL_DEPENDENCY_BLUEPRINT.json`.
