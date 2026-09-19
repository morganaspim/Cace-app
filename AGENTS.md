# Working on CACE

CACE is a proprietary computational research environment owned by Emmanuel Spiro. Read `LICENSE` and `NOTICE`. AI assistance is optional; the runtime and verification path must not require an AI service.

## Start here

Read these in order before changing scientific or verification behavior:

1. `CACE_AGENT_BOOTSTRAP.json` — single-entry machine-readable build/trust handoff.
2. `CACE_BUILD_LITE.json` — low-cost deterministic build/test optimizer for coding agents.
3. `CACE_PAYMENT_POLICY.json` — canonical public payment-wallet policy; do not invent replacement wallets.
4. `CACE_DEPLOYMENT_BOUNDARY.json` — browser-only public surface and hardened private/local service policy.
5. `CACE_TRIAL_ACCOUNT_POLICY.json` — one-person/one-trial and non-destructive expiry policy.
6. `CACE_PUBLIC_HELP_POLICY.json` — customer-help completeness and proprietary-leakage boundary.
7. `CACE_MULTI_TENANT_POLICY.json` — multi-user tenancy, isolation, persistence and load-balancing policy.
8. `CACE_PUBLIC_SERVICE_POLICY.json` — global public signup/access and country policy.
9. `CACE_TELEMETRY_PRIVACY_POLICY.json` — essential heartbeat, product analytics and proof-contribution privacy boundaries.
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


## Unknown-feature implementation protocol

A coding agent must attempt every required production feature. It must not omit,
stub, silently defer, or replace a requested feature merely because its first
implementation approach is unclear.

When the agent does not know how to implement a feature safely:

1. preserve the current architecture and identify every subsystem/invariant the
   feature touches;
2. generate **10 materially different implementation approaches** by default
   (fewer only when the design space is genuinely smaller);
3. rank the approaches using this ordered rubric:
   - architecture preservation / compatibility;
   - correctness and evidence-boundary preservation;
   - security / privacy / least privilege;
   - implementation tractability;
   - testability and bug-sweep coverage;
   - reuse of existing CACE modules/tools;
   - compute/build cost;
   - maintainability and future extension;
4. use CACE Build Lite and other applicable CACE mathematical/scientific tools
   to analyze dependencies, critical paths, cache reuse, resource limits, and
   invariants before selecting the implementation;
5. choose the highest-ranked viable approach that does not weaken an existing
   architecture;
6. if the repository lacks a needed capability, build a narrowly scoped custom
   helper/tool with a typed contract, deterministic behavior where practical,
   explicit limits, unit/regression tests, and no extra authority;
7. after every confirmed defect, run the normal CACE bug-flush loop:
   reproduce -> classify defect family -> root-cause fix -> sibling/repository
   sweep -> regression test -> permanent structural guard where possible;
8. run Build Lite again and then the required merge/proof/security gates;
9. if no approach is actually safe/complete, leave the feature visibly
   incomplete with the ranked alternatives and blocking reason. Never fake a
   working implementation.

### Architecture preservation rule

All established CACE architectures are cumulative constraints unless an explicit
approved migration supersedes them. A builder may refactor an implementation,
but it must preserve the behavior/contracts of:

- scientific typed-object and graph semantics;
- evidence/verification and proof qualification;
- security/trust boundaries;
- account/network/capability separation;
- AI non-authority;
- heartbeat/economy separation from proof truth;
- provenance/log retention;
- source-secrecy/commercial boundaries;
- existing public APIs/schema compatibility or an explicit migration path;
- user-requested feature goals recorded in the goal registry/idea ledger.

Before a substantial refactor, record which architectures are affected and how
each invariant is preserved. “Simpler to generate” is never sufficient reason to
delete or weaken an architecture.


## Browser-only public surface

For a production CACE build, the **webapp/gateway is the only client-visible
service**. The browser must never connect directly to scientific workers, local
AI/model servers, databases, network-pairing transport, Math Coin/Monero wallet
services, filesystem workers, native kernels, or the Lean qualification runner.

Machine-readable authority: `CACE_DEPLOYMENT_BOUNDARY.json`.

Required shape:

```
Browser / client
       |
    HTTPS/WSS
       |
 CACE Web Gateway        <-- only public application surface
       |
 typed private IPC
       |
 Hardened Local/Private Layer
       +-- orchestrator
       +-- scientific runtime + C++/GPU workers
       +-- local-AI capability broker
       +-- account/protein database
       +-- directional AI-economy pairing broker
       +-- Math Coin broker
       +-- canonical Monero wallet broker
       +-- durable evidence/provenance storage
       +-- isolated Lean qualification runner
```

Hosted builders such as Base44 or Gemini AI Studio may generate the browser
surface and gateway integration, but they must not move canonical computation,
wallet custody, proof authority, secrets, or scientific verification into
client-side/generated code merely for convenience.

Protected services should bind only Unix-domain sockets, loopback, or a private
service network; they must not listen on public interfaces. Use least-privilege
service identities, default-deny firewall/egress policy, read-only roots where
practical, no-new-privileges/capability dropping, bounded resources, typed IPC,
server-side secrets, and auditable privileged operations.

The public gateway treats all browser state as hostile input and revalidates
schema, authorization, sizes, rates, paths and capabilities server-side.


## Full-production "just works" requirement

The intended product is a **full-featured, production-grade mathematics and
sciences playground that just works** for an ordinary supported user. A coding
agent must not turn CACE into a demo, thin calculator, documentation site, or
collection of disconnected prototypes.

Production startup should automatically:

- perform platform/runtime preflight checks;
- initialize required local account/data/work directories safely;
- start the hardened private/local service plane with the strongest practical
  sandbox controls available on the host;
- expose only the CACE web gateway to the browser/client;
- detect optional CPU/GPU/AI/scientific backends;
- degrade visibly when an optional backend is missing rather than weakening
  evidence/security rules;
- provide a usable canvas/module/help experience without requiring a developer
  to manually wire ordinary features.

Machine-readable security authority remains `CACE_DEPLOYMENT_BOUNDARY.json`.
See `docs/JUST_WORKS_SELF_SANDBOXING.md`.

## Trial and one-person account rule

The free trial requires **no credit card** and is granted once per verified
person/user identity anchor. Browser cookies, a new email form submission, or a
fresh account row are not sufficient to create a new trial.

The production auth adapter must provide a stable verified subject from which
the server derives an opaque person key. Trial entitlement is stored separately
from the account row. If the same person returns, recover/merge the existing
account; do not grant another trial.

Trial expiry must be non-destructive. CACE must never encrypt, corrupt, delete,
or hold user data hostage. An expired unlicensed account retains at least
sign-in, view, export/download, delete, account recovery, help and license
management. Premium execution/network/economy features may become unavailable
until licensed.

Authority: `CACE_TRIAL_ACCOUNT_POLICY.json`.
Executable core: `cace_studio/trial_entitlement.py`.

## Customer-safe complete help requirement

Every production build must provide customer help for every customer-facing
feature and every registered module, with at least:

- two examples for each feature;
- two direct-use examples for each module;
- two combined-module examples for each module;
- visible input/output/parameter type/unit contracts;
- public evidence/rigor explanations;
- safe compatible-connection suggestions.

Generate it from the live registry:

```sh
python scripts/generate_public_help.py
```

The generated reference belongs at
`docs/help/generated/CACE_PUBLIC_HELP.md` and its machine-readable companion.

The help layer must **not** disclose proprietary CACE equations, custom
mathematical derivations, algorithms, source paths, class/function names,
theorem bodies, Lean implementation details, hidden defaults/coefficients,
proof artifacts, credentials, database internals, service internals or prompts.
Explain what a module looks for and how to use/connect it, not how CACE
implements it internally.

Authority: `CACE_PUBLIC_HELP_POLICY.json`.


## Multi-user / multi-tenant production rule

CACE production must support many concurrent users/accounts without turning the
system into one shared-privilege runtime or maintaining source-code clones per
user.

Preferred architecture:

- shared stateless web/API gateway replicas;
- tenant/account-aware control plane;
- durable logical CACE instance per account/user;
- isolated tenant/job sandboxes for private execution;
- tenant-scoped persistent data/evidence/protein/account state;
- durable tenant-aware job queues and fair scheduling;
- optional warm sandboxes for interactive latency;
- suspend/resume or worker replacement for idle/failed compute;
- isolated proof qualification outside ordinary tenant workers.

Users running local CACE/local-AI on their own network should initiate outbound
authenticated connections to the CACE gateway/broker. Do not require customers
to open inbound ports on home/lab/office networks.

Never clone and independently mutate the CACE source tree for each user. Run a
reviewed immutable release image and bind user-specific state through a tenant
instance manifest.

Cross-tenant access is denied by default. Collaboration/economy pairing must be
explicitly capability-authorized.

Machine-readable authority: `CACE_MULTI_TENANT_POLICY.json`.
Design: `docs/MULTI_TENANT_SERVICE_ARCHITECTURE.md`.


## Public signup and improvement telemetry

Production CACE should expose one stable HTTPS webapp URL where eligible users
can sign up/recover an account and receive their own durable logical CACE
instance. The actual production domain is deployment configuration; do not
invent or hard-code an unowned domain.

Requested country policy:

- default allow;
- deny CN;
- deny KP.

Enforce this at the trusted edge/gateway and again on signup/session/local-agent
broker registration. Country geolocation is a policy/risk signal, not perfect
proof of physical location, and it never replaces sanctions/export/end-user
compliance.

Machine authority: `CACE_PUBLIC_SERVICE_POLICY.json`.

### Telemetry lanes

All hosted instances may emit **essential operational heartbeat** needed for
service reliability, security and capacity planning. Essential telemetry is
strictly allowlisted and may include version, health, queue/resource buckets,
job/error counts, feature heartbeat counts and proof-status **counts only**.

Essential telemetry must never include raw scientific inputs, equations,
theorem/proof text, AI prompts/responses, protein content, local filenames,
precise location or wallet secrets.

Product analytics used to improve CACE or inform internal sales/customer-success
strategy use a separate privacy lane with the required notice/consent/legal
basis, minimization, retention and opt-out/withdrawal controls.

Actual proof/theorem/research artifact contribution is a third lane and is
**off by default**. It requires separate explicit project/account opt-in and
contribution/IP terms.

Authority: `CACE_TELEMETRY_PRIVACY_POLICY.json`.
Executable allowlist: `cace_studio/telemetry_contract.py`.


## Multi-window semantic routing

CACE must support multiple independent windows and monitors.

Do not attempt to make the operating system use non-rectangular windows as the scientific coordinate model. Keep physical windows in ordinary rectangular screen space and route them from a separate semantic workspace coordinate system.

Supported/planned semantic geometries include Cartesian, hex axial/cube, radial/polar, hyperbolic, Voronoi/power, Hilbert/Morton, simplex/barycentric, Gaussian/Eisenstein complex lattices, recursive/fractal addressing and optional 3D/spherical layouts.

User pins override automatic routing. Preserve spatial memory and keep proof/evidence windows near the results they explain. Persist layout state separately from scientific hashes/evidence/proof.

Authority: `CACE_MULTI_WINDOW_ROUTING_POLICY.json`.
Design: `docs/MULTI_WINDOW_SPATIAL_ROUTING.md`.
