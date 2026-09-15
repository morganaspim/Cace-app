# CACE Formal

Pinned Lean 4 / mathlib project for CACE theorem-prover evidence.

## Bootstrap

1. Install `elan` using the official Lean installer.
2. `cd formal/cace_formal`
3. `lake update`
4. `lake exe cache get`
5. `lake build`

This repository pins Lean to v4.32.1 and pins mathlib to the exact commit recorded by the formal project manifest/workflow. Qualification is never promoted from source inspection alone: the pinned target must compile, pass the kernel axiom audit, and produce an exact-head attestation.

## Qualification runtime

The v3.30 qualification workflow runs on the repository's ARM64 self-hosted runner because hosted-runner attempts have not provided a usable qualification environment. The runner environment is container-like (PID 1 is not systemd), so `svc.sh`/systemd service installation is not available inside that environment.

To reduce infrastructure-induced false failures, the runner now uses a detached user-space watchdog outside the Actions worker process. The watchdog maintains a heartbeat, restarts `Runner.Listener` if the manual listener disappears, and records persistent formal-build telemetry (active Lean/Lake processes, `.olean` count/newest compiled files, memory, disk, and cgroup memory events). This watchdog is CI infrastructure only: it does not alter Lean sources, theorem statements, the pinned Lean/mathlib versions, the kernel axiom whitelist, or the attestation requirements.

A qualification result remains unqualified until the required workflow gates themselves report success. Runner/watchdog health is not proof evidence and cannot substitute for compilation or kernel checking.

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
