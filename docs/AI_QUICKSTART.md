# CACE for AI agents and command-line tools

The development package version is 3.36.0.dev1. It is not a production release and does not imply that every v3.32-v3.36 subsystem is qualified. Module versions, mathematical claim status and historical roadmap milestones use separate numbering.

Start with `AGENTS.md`, `AI_REPO_MAP.json`, `docs/STATUS.md`, `docs/ARCHITECTURE.md`, `docs/CONSTITUTION.md`, `docs/CLAIMS.md` and `docs/PRODUCTION_READINESS.md`.
## Cross-chat continuity

Before continuing an existing CACE workstream, read `docs/CROSS_CHAT_HANDOFF.md` and `docs/CHAT_IDEA_LEDGER.md`. If GitHub is unavailable from the current chat but ChatGPT Library is available, retrieve the mirrored copies from `/CACE CONTINUITY/`.

The handoff is navigation only. Always re-query the current branch/PR/Actions state before proof, qualification, deployment, or release actions. During each substantive CACE chat, preserve new meritorious ideas in the ledger/goal registry and refresh the handoff at a natural stopping point. Documentation and conversational continuity never create verification evidence.


## Setup

Python 3.11+ and a C++20 compiler are required for the full regression suite. Python 3.13.15 is used by the current CI workflows.

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[test]' cmake
cmake -S cpp -B cpp/build -DCMAKE_BUILD_TYPE=Release
cmake --build cpp/build --parallel 2
ctest --test-dir cpp/build --output-on-failure
python -m pytest
```

The GUI additionally needs `.[gui]`. Ed25519 provenance attestations need `.[attest]`. Neither registry inspection nor ordinary headless graph execution requires Qt or an AI provider.

## Generate deterministic AI navigation indexes

The repository contains a deterministic generator rather than a manually duplicated compiled-source file. Generate the navigation artifacts when an AI or tool needs a compact repository map:

```sh
python scripts/generate_ai_indexes.py
```

It produces:

- `MODULE_CATALOG.json`
- `CLAIM_CATALOG.json`
- `PROOF_DEPENDENCY_GRAPH.json`
- `SOURCE_INDEX.json`
- `generated/CACE_SOURCE_CONTEXT.txt`

These are generated navigation aids, **not verification evidence**. Canonical claim status remains in `cace_studio/data/claim_registry.json` and `cace_studio/data/proof_ledger.json`; formal source remains under `formal/cace_formal/`.

## Discover and execute

```sh
python -m cace_studio.cli registry
python -m cace_studio.cli run examples/verified_quadratic.cace --seed 0 --output report.json
python -m cace_studio.cli fingerprint examples/verified_quadratic.cace
```

The installed short command is `cace`. Registry JSON includes module IDs, input/output ports, parameters, declared maturity, assumptions and declared proof status. Declaration is not verification. Run JSON includes actual verification records, certificates, outputs, claim decisions and seed.

CLI schema version: 1. Run reports retain their own `report_schema` version. Exit codes are: 0 = command success or every emitted verifier passed with at least one record; 1 = a verifier failed; 2 = invalid input/execution/serialization error; 3 = computation completed but verification was absent/incomplete or an eligibility policy was not satisfied. Code 0 does not mean the whole application is formally proved.

Errors are JSON on stderr. With `--output`, supported commands write the report there. Default graph execution uses the CPU. For each scientific claim inspect its method, assumptions, limitations and metrics.

## Local AI

CACE execution and verification do not depend on AI. Studio local-AI support is off by default and is restricted to loopback providers such as Ollama, LM Studio or llama.cpp/OpenAI-compatible local endpoints. AI output is never verification evidence.

Install GUI support and configure the provider from Studio rather than editing source:

```sh
python -m pip install -e '.[gui]'
cace-studio
```

## Formal v3.30 qualification checks

From `formal/cace_formal`, install the version in `lean-toolchain` using elan, then use the exact audited dependency closure rather than downloading/building unrelated historical modules:

```sh
MATHLIB_NO_CACHE_ON_UPDATE=1 lake update
lake build +Cache.Main
lake env lean --run .lake/packages/mathlib/Cache/Main.lean get CACEFormal/V330AxiomAudit.lean
lake build CACEFormal.V330AxiomAudit
lake env lean CACEFormal/V330AxiomAudit.lean
```

The authoritative GitHub workflow additionally checks the exact Mathlib commit, rejects unfinished proof tokens, applies the kernel-axiom allowlist, records the audited source-bundle hash and emits an attestation only after success. Inspect the dependency manifest and axiom log in its diagnostic artifact. Do not treat a downloaded `.olean`, a historical workflow result or an old attestation as proof of edited source.

Formal qualification is fail-closed: a module-local FORMAL result cannot promote itself. The canonical claim registry and proof ledger must bind the exact qualified commit and proof-artifact digest, and qualification-sensitive source drift requires a fresh attestation.

## Provenance, signatures and E5 cross-verification

Evidence bundles, Merkle roots and signatures establish artifact identity/integrity and verifier attestations; they do not create mathematical proof.

With the optional attestation dependency installed:

```sh
python -m pip install -e '.[attest]'
cace-attest keygen --private-key verifier.key --public-key verifier.pub
cace-attest verify verifier-attestation.json
```

`cace-attest sign` binds an independent-reproduction statement to an exact CACE evidence-bundle hash, claim ID, qualified commit and proof-artifact hash. `cace-attest cross-verify` evaluates E5 eligibility only after the canonical claim is already current-head PASS qualified and multiple distinct approved verifier identities/keys attest the same exact artifact context. E5 does not self-promote proof status.

## Distribution

The Python regression workflow builds a wheel, installs it in a separate environment and tests registry access outside the checkout. Passing runs expose the wheel as a GitHub Actions artifact. This wheel provides the Python interface; the optional C++ runtime still requires its platform build.

Compiled Lean/C++ binaries are platform/toolchain-specific and do not make source easier to review. Portable source, contracts, schemas, generated navigation indexes, tests and exact qualification artifacts are the primary AI integration surface. A private repository still requires the connecting agent to have repository access.
