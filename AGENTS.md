# Working on CACE

CACE is a proprietary computational research environment owned by Emmanuel Spiro. Read `LICENSE` and `NOTICE`. AI assistance is optional; the runtime and verification path must not require an AI service.

## Start here

Read these in order before changing scientific or verification behavior:

1. `CACE_AGENT_BOOTSTRAP.json` — single-entry machine-readable build/trust handoff.
2. `CACE_BUILD_LITE.json` — low-cost deterministic build/test optimizer for coding agents.
3. `CACE_PAYMENT_POLICY.json` — canonical public payment-wallet policy; do not invent replacement wallets.
3. `docs/CROSS_CHAT_HANDOFF.md` — cross-chat continuity, latest preserved frontier, and refresh protocol.
3. `docs/CHAT_IDEA_LEDGER.md` — append-only chat-derived research/product idea memory.
4. `docs/BUILD_AND_TRUST_GUIDE.md` — unified product, rigor, security, bug-flush, provenance and build architecture.
5. `docs/STATUS.md` — current source/qualification state.
6. `docs/ARCHITECTURE.md` — subsystem boundaries and trusted-computing-base model.
7. `docs/SECURITY_ARCHITECTURE.md` — trust zones, threats, isolation and secrets policy.
8. `docs/CONSTITUTION.md` — non-negotiable project rules.
9. `docs/CLAIMS.md` — claim registry, proof ledger and fail-closed promotion policy.
10. `docs/BUG_FLUSH_ARCHITECTURE.md` — permanent defect-class prevention loop.
11. `docs/PROVENANCE_ATTESTATION.md` — content identity, independent logs and evidence preservation.
12. `docs/ROADMAP.md` — dependency-ordered implementation milestones.
13. `docs/MASTER_BUILD_SPEC.md` — consolidated durable product goals and acceptance criteria.
14. `docs/GOAL_REGISTRY.json` — machine-readable goal registry for agents/tools.
15. `docs/AI_QUICKSTART.md` — headless commands and JSON interfaces.
16. `AI_REPO_MAP.json` — machine-readable navigation.
17. The relevant release/proof-scope file for the feature being changed.

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

For cross-chat continuity, every substantive CACE chat/agent session should also read `docs/CROSS_CHAT_HANDOFF.md`, deduplicate and append meritorious chat-derived ideas in `docs/CHAT_IDEA_LEDGER.md`, refresh the handoff when the live frontier materially changes, and mirror both files to the ChatGPT Library continuity folder when that surface is available. Handoff snapshots are navigation only: always re-query live GitHub/CI state before acting.

## Provenance

Future immutable provenance uses content addresses, deterministic Merkle bundles, signed attestations, an append-only transparency ledger and optional external timestamp/blockchain anchoring. This establishes tamper/provenance evidence only and never proves a mathematical claim. See `docs/PROVENANCE_ATTESTATION.md`.

## Repository-only reconstruction requirement

A repository-reading agent must be able to reconstruct the intended webapp, proof/evidence architecture, security boundaries, bug-flush process, provenance/log-retention policy, deployment shape, and acceptance criteria without private chat history. If that is not possible from `CACE_AGENT_BOOTSTRAP.json` and the documents it references, improve repository discoverability before relying on conversational context.


## Production code-builder mode

This repository is intended to be usable by GitHub-connected coding agents and
full-stack builders such as Base44, Gemini AI Studio, Codex, and equivalent tools.

When acting as a code builder, **build the complete production CACE application**.
Do not replace the application with a mock, static prototype, simplified
calculator, disconnected front end, or second scientific semantics.

Before broad build/test work:

1. read `CACE_AGENT_BOOTSTRAP.json`, `CACE_CODE_BUILDER_BOOTSTRAP.json`,
   `CACE_BUILD_LITE.json`, `docs/CROSS_CHAT_HANDOFF.md`, and the relevant source;
2. make the smallest coherent change;
3. run CACE Build Lite against the real changed paths:

   ```sh
   python scripts/cace_build_lite.py --repo . --git-base origin/main --profile quick --commands
   ```

4. execute fail-fast/cheap batches first;
5. fix failures before expanding the frontier;
6. use the `merge` profile before merge-quality claims;
7. use the `proof` profile for formal-source work, but never treat Build Lite
   output or cache state as Lean qualification.

Build Lite is intentionally small and inexpensive. It performs dependency-DAG,
critical-path, exact-content-cache, and resource-bounded scheduling mathematics.
It may optimize the builder's work plan, but it has no authority to change
scientific truth, proof status, security policy, or user permissions.

### Hosted-builder rules

- GitHub source is authoritative unless an explicit approved connector writes an
  exact reviewed change back to GitHub.
- Preserve the canonical Python graph/module/evidence runtime; browser/mobile
  presentation layers call it through typed APIs rather than reimplementing
  scientific truth in JavaScript or generated backend logic.
- Keep Lean/formal qualification isolated from untrusted application requests.
- Never place repository secrets, signing keys, wallet private keys, exchange
  credentials, or production database secrets into prompts, generated client
  bundles, repository files, or model context.
- Account/network/economic features are application state and never proof evidence.
- If a hosted builder cannot faithfully implement a subsystem, leave the
  canonical subsystem intact and surface the limitation rather than silently
  replacing it with a weaker implementation.
- Read `docs/MASTER_BUILD_SPEC.md` and `docs/GOAL_REGISTRY.json` before
  declaring the production app complete.


### Canonical Monero wallet rule

CACE already has an existing production Monero receive wallet from the earlier
application/software assets. Coding agents **must not create or substitute a new
Monero wallet/address**.

Canonical public XMR receive address:

`482ivJw4VqAaRvixSG84DgDum33SoBfnNiMxngMKn7etfKP1mwG2ZskTLVwRAhPmPDcb5iqLGkKdJbQ6DJmzqePPPxp3tmQ`

Machine-readable authority: `CACE_PAYMENT_POLICY.json`.

Rules:

- the address is public configuration, not a secret;
- never place Monero spend keys, view keys, wallet RPC credentials, exchange
  credentials, seeds, or mnemonics in source, prompts, browser code, logs, or
  model context;
- if production invoice/subaddress support is implemented, it must derive from
  the same existing wallet custody rather than creating a replacement wallet;
- the local AI Math Coin wallet/capability is a separate identity and must not
  be confused with the canonical XMR receive wallet;
- payment/wallet state never changes scientific proof or evidence.
