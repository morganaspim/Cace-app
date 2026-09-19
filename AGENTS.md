# Working on CACE

CACE is a proprietary computational research environment owned by Emmanuel Spiro. Read `LICENSE` and `NOTICE`. AI assistance is optional; the runtime and verification path must not require an AI service.

## Start here

Read these in order before changing scientific or verification behavior:

1. `CACE_AGENT_BOOTSTRAP.json` — single-entry machine-readable build/trust handoff.
2. `docs/BUILD_AND_TRUST_GUIDE.md` — unified product, rigor, security, bug-flush, provenance and build architecture.
3. `docs/STATUS.md` — current source/qualification state.
4. `docs/ARCHITECTURE.md` — subsystem boundaries and trusted-computing-base model.
5. `docs/SECURITY_ARCHITECTURE.md` — trust zones, threats, isolation and secrets policy.
6. `docs/CONSTITUTION.md` — non-negotiable project rules.
7. `docs/CLAIMS.md` — claim registry, proof ledger and fail-closed promotion policy.
8. `docs/BUG_FLUSH_ARCHITECTURE.md` — permanent defect-class prevention loop.
9. `docs/PROVENANCE_ATTESTATION.md` — content identity, independent logs and evidence preservation.
10. `docs/ROADMAP.md` — dependency-ordered implementation milestones.
11. `docs/MASTER_BUILD_SPEC.md` — consolidated durable product goals and acceptance criteria.
12. `docs/GOAL_REGISTRY.json` — machine-readable goal registry for agents/tools.
13. `docs/AI_QUICKSTART.md` — headless commands and JSON interfaces.
14. `AI_REPO_MAP.json` — machine-readable navigation.
15. The relevant release/proof-scope file for the feature being changed.

Always inspect exact-commit Actions evidence before describing current source as formally qualified or production-ready. Historical reports, release notes and example outputs are snapshots, not inherited current-head evidence.

## Repository map

- `cace_studio/core/`: graph execution, verification records, certificates, claim/proof governance, serialization, numerical/device infrastructure.
- `cace_studio/modules/`: independently registered scientific/research modules. Version labels are not maturity evidence.
- `cace_studio/gui/`: PySide6 visual experiment editor and scientific UI.
- `cace_studio/cli.py`: headless JSON registry/experiment interface.
- `cpp/`: C++20 runtime and native smoke/regression tests.
- `formal/cace_formal/`: pinned Lean project.
- `schema/`: machine-readable contracts.
- `tests/`: behavioral, adversarial and regression tests.
- `examples/`: `.cace` inputs and historical output artifacts.
- `docs/`: current architecture/status/policy and preserved historical context.

## Required scientific discipline

Preserve explicit hypotheses and unresolved obligations. Never replace a theorem obligation with an axiom, `sorry`, numerical result, caller-supplied assertion or AI suggestion and describe it as proved. Conditional theorems must retain their conditions in code, documentation and public claim scope.

Evidence classes are not interchangeable. Numerical tests do not prove continuum theorems. Exact/symbolic certificates prove only what their checker verifies. Interval evidence applies only to the certified bounds. A successful Lean build establishes compiled statements under their explicit hypotheses and trusted axioms; it is not an end-to-end proof of the Python/C++ application. GPU/CPU agreement is backend evidence, not mathematical proof.

`FAIL`, `NOT_RUN` and absent verification must remain visible. No verifier or skipped verifier is not success. Module metadata describes intent, not executed evidence.

## Formal promotion rule

Module-local `FORMAL + PASS` is insufficient for public formal evidence. Promotion is reserved to the canonical claim registry/proof ledger and must satisfy the fail-closed gate, exact commit/artifact provenance and qualification-drift policy. A later source commit may inherit an attestation only when the drift checker proves that no qualification-sensitive source changed.

Never edit canonical provenance merely to make a test green. Never weaken a negative/fault-injection test to preserve a desired status.

## Implementation discipline

Each new capability needs a stable module/entry point, typed contract, assumptions, meaningful tests, evidence level, limitations and reproducible commands. Prefer strengthening a canonical subsystem over adding another versioned wrapper. Preserve historical artifacts but do not let historical compatibility prevent removal of unsupported current claims.

Python orchestrates; C++ is for justified expensive kernels. Formal proof source stays in the Lean project. GUI code must consume core contracts rather than invent separate scientific semantics.

For releases, require the appropriate combination of full Python/native tests, package-install checks, pinned Lean build/kernel audit, source/artifact provenance, compatibility evidence and security/reproducibility checks on the qualified source state.

## AI and external agents

AI may inspect, explain, propose and edit, but AI output is never verification evidence. The project must remain usable with AI completely disabled. Future local-provider support should be no-code for users but remain outside the evidence trusted-computing base.

When changing the repository for agent discoverability, generate or derive indexes from canonical source wherever practical; do not maintain conflicting duplicate source trees. `AI_REPO_MAP.json` is navigation, not a substitute for reading the canonical implementation and claim data.

When the user states a new CACE goal with clear product, scientific, engineering, proof-rigor, or research merit, persist it in `docs/GOAL_REGISTRY.json` and update `docs/MASTER_BUILD_SPEC.md` when it changes architecture or long-term behavior. Label research ideas as research; documentation must never promote them to verified claims. Prefer a documentation-only branch while an exact-head formal qualification is in flight.

## Provenance

Future immutable provenance uses content addresses, deterministic Merkle bundles, signed attestations, an append-only transparency ledger and optional external timestamp/blockchain anchoring. This establishes tamper/provenance evidence only and never proves a mathematical claim. See `docs/PROVENANCE_ATTESTATION.md`.

## Repository-only reconstruction requirement

A repository-reading agent must be able to reconstruct the intended webapp, proof/evidence architecture, security boundaries, bug-flush process, provenance/log-retention policy, deployment shape, and acceptance criteria without private chat history. If that is not possible from `CACE_AGENT_BOOTSTRAP.json` and the documents it references, improve repository discoverability before relying on conversational context.
