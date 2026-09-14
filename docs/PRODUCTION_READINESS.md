# CACE readiness and ranked implementation plan

Audit date: 2026-09-14. Development line: roadmap/v3.30-proof-strengthening.
Assessment: **research/development; production readiness not established**.

The last observed formal run 34889429471 failed during Mathlib cache transfer (OpenSSL
unregistered scheme). Claim-promotion Python tests passed in that run; Lean compilation and
the axiom audit did not execute. Python regression run 34889880923 was queued at audit time.
Consult Actions for subsequent results. No source change alone changes this assessment.

## Priority order and acceptance evidence

| Rank | Work | Current state | Completion criterion |
| --- | --- | --- | --- |
| 1 | Honest verification and reproducible execution | This change fixes empty/NOT_RUN success, adds CLI and CI native/package checks, repairs formal build isolation and configures TLS trust | Full Python/native/package checks and pinned Lean/axiom audit pass on the exact commit; failures remain visible |
| 2 | Close H1 and H(div) analysis | Open: unconditional Schwartz graph regularizers; Bessel/Riesz reconstruction identity | Explicit construction, graph-norm convergence and H1 converse compile without extra axioms or supplied reconstruction/density hypotheses |
| 3 | Carry the completed domains through continuum theorems | Conditional bridges exist | Weak Green, boundary orthogonality and Prager-Synge use identified distributional spaces with domain/boundary/coefficient hypotheses and checked dependencies |
| 4 | Connect executable results to formal statements | Exact certificates and bridges exist; whole program is not proved | Specification-to-code mapping, independent certificate replay, adversarial malformed inputs, and documented trusted computing base per supported claim |
| 5 | Qualify production distribution | Wheel CI added; native packaging, dependency lock and compatibility coverage remain | Clean installs on supported OS/architectures/Python versions, native artifacts, locked dependency builds, upgrade tests, performance/resource budgets, release provenance |
| 6 | Audit prior solver milestones against actual behavior | Historical native, sparse, adaptive and reliability modules exist | Per-module qualification matrix separating implemented algorithms, imported lemmas, conditional proofs, synthetic fixtures and measured experiments; remove unsupported maturity claims |
| 7 | Complete mature FEM/adaptive theory where audit finds gaps | Earlier plan includes equilibrated flux, Cea/Lax-Milgram, Bramble-Hilbert, Aubin-Nitsche, efficiency and adaptivity | Explicit assumptions and dependency DAG, meaningful independent tests and formal proofs for the advertised scope |
| 8 | Resume foundational geometry roadmap | Prior plan; coverage in this solver repository not established | Certified interval/algebraic ownership with unresolved boundary cases; one specified aperiodic locator with termination/coverage/disjointness; bounded CVP comparisons against exhaustive reference |
| 9 | Broader mathematics/physics extensions | Research backlog | Defined model and validated prerequisites; no general polynomial-time CVP, quantum speedup, new physics or full classification claim from numerical evidence |

Ranks express dependency and risk reduction, not a promise that open research can be finished by CI.
Do not add duplicate module wrappers for features that already exist; audit their implementations first.
AI access improvements accompany rank 1 because they make the remaining work discoverable and reproducible.

## Evidence boundaries

- Runtime regression tests are evidence for the tested cases.
- Exact arithmetic certificates prove only the claims checked by their checker.
- Lean proves formal statements under their explicit hypotheses and trusted foundational axioms.
- The v3.30 regularizer criteria do not construct regularizers.
- The H1 reconstruction theorem still takes the reconstruction identity as a hypothesis.
- A production release additionally needs operational, packaging and compatibility qualification.
- External mathematical review and independent reproduction remain external trust boundaries.

## Changes in this increment

The package and import versions are aligned at 3.30.0.dev1.
The headless CLI exposes module contracts and run evidence without Qt or an AI dependency.
All-verifiers-passed now requires at least one record and every record to be PASS.
Historical tests that intentionally include NOT_RUN now assert incomplete verification.
CMake registers the native smoke executable with CTest. CI builds the native runtime before Python
tests, checks an installed wheel outside the checkout, and publishes the wheel only after success.
The formal job uses a fresh owned temporary directory, a system CA bundle with TLS verification,
a Mathlib SHA check, bounded cache-download time, and dependency/axiom diagnostic artifacts.

These changes improve readiness; the proof and release gates above remain mandatory.
