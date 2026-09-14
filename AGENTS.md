# Working on CACE

CACE is a proprietary computational research environment owned by Emmanuel Spiro.
Read LICENSE and NOTICE. AI assistance is optional; the headless runtime does not require an AI service.

## Start here

1. Read docs/PRODUCTION_READINESS.md for the current ranked work and proof boundaries.
2. Read docs/AI_QUICKSTART.md for commands, JSON contracts, and exit codes.
3. Inspect RELEASE_v3.30.json and V330_PROOF_STRENGTHENING.md for the exact mathematical scope.
4. Check GitHub Actions on the exact commit before describing it as validated.
   Historical reports in examples/ and release manifests are snapshots, not current-head evidence.

## Repository map

- cace_studio/core/: graph execution, verification records, certificates, claim policy, native bridge.
- cace_studio/modules/: independently registered research modules; version labels are not maturity evidence.
- cace_studio/cli.py: headless JSON registry and experiment execution.
- cpp/: C++20 runtime, C ABI and native smoke test.
- formal/cace_formal/: Lean project; lean-toolchain and lakefile.lean pin dependencies.
- tests/: Python regression suite. Build cpp/build before the full suite.
- examples/: .cace experiment inputs and historical output artifacts.

## Required discipline

Preserve explicit hypotheses and unresolved obligations. Never replace a theorem obligation with an
axiom, sorry, numerical result, or a caller-supplied assertion and call it proved.
A conditional theorem must retain its conditions in documentation.
A successful Lean build establishes only the compiled statements under their hypotheses; it is not
an end-to-end proof of the Python/C++ application or of production readiness.

Tests must exercise behavior, including refusal of invalid evidence. No verifiers or NOT_RUN records
must never be described as all verifiers passed. Module metadata describes intent; use actual run
records as evidence. Public resolution claims require the separate artifact-bound claim policy and
external review/reproduction; external identities are not authenticated by CACE.

Each new feature needs a module/entry point, contract, assumptions, meaningful tests, evidence level,
limitations, and reproducible commands. Prefer small changes to a ranked blocker over adding another
versioned wrapper. Do not silently change historical reports or promote release status.
For releases, require full Python and native tests, pinned Lean build and axiom audit, and package
installation checks on the same commit. Keep generated binaries out of the source tree; use CI
artifacts with their source commit and platform identified.
