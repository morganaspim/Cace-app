# CACE for AI agents and command-line tools

The development package version is 3.30.0.dev1. It is not a production release.
Module versions and historical roadmap milestones use separate numbering.
Start with AGENTS.md and docs/PRODUCTION_READINESS.md.

## Setup

Python 3.11+ and a C++20 compiler are required for the full test suite. Python 3.13.15 is used in CI.

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[test]' cmake
cmake -S cpp -B cpp/build -DCMAKE_BUILD_TYPE=Release
cmake --build cpp/build --parallel 2
ctest --test-dir cpp/build --output-on-failure
python -m pytest
```

The GUI additionally needs `.[gui]`. Neither registry inspection nor headless execution imports Qt.

## Discover and execute

```sh
python -m cace_studio.cli registry
python -m cace_studio.cli run examples/verified_quadratic.cace --seed 0 --output report.json
```

The installed short command is `cace`. Registry JSON includes module IDs, input/output ports,
parameters, declared maturity, assumptions and declared proof status. Declaration is not verification.
Run JSON includes actual verification records, certificates, outputs, claim decisions and seed.

CLI schema version: 1. Run reports retain their own report_schema version.
Exit codes: 0 = registry success or every emitted verifier passed with at least one record;
1 = a verifier failed; 2 = invalid input/execution/serialization error;
3 = computation completed but verification was absent or incomplete.
Code 0 does not mean the whole application is formally proved.
Errors are JSON on stderr. With --output, the report is written to that path.
Default execution uses the CPU. For each numerical claim inspect its method, assumptions and metrics.

## Formal checks

From formal/cace_formal, install the version in lean-toolchain using elan, then:

```sh
MATHLIB_NO_CACHE_ON_UPDATE=1 lake update
lake build +Cache.Main
lake env lean --run .lake/packages/mathlib/Cache/Main.lean get
lake build CACEFormal
lake env lean CACEFormal/V330AxiomAudit.lean
```

The GitHub workflow additionally checks the resolved Mathlib commit, rejects unfinished tokens,
checks the axiom allowlist, and emits an attestation only after success.
Inspect the dependency manifest and axiom logs in its diagnostic artifact.
Do not treat a downloaded .olean or an old attestation as proof of edited source.

## Distribution

The Python regression workflow builds a wheel, installs it in a separate environment, and tests
registry access outside the checkout. Passing runs expose the wheel as a GitHub Actions artifact.
This wheel provides the Python interface; the optional C++ runtime still requires its platform build.
Compiled Lean/C++ binaries are platform/toolchain-specific and do not make source easier to review.
The portable entry points, contracts, tests and source are the primary AI integration.
A private repository still requires the connecting agent to have repository access.
