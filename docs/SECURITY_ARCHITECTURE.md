# CACE Security Architecture

Status: architectural security requirements and trust boundaries. This document is not a claim that every control is already implemented or independently audited.

## 1. Security objective

CACE must let users explore, compute, visualize, prove, and reproduce scientific work without allowing convenience layers such as the browser UI, plugins, local AI, remote deployment, or CI orchestration to silently weaken mathematical rigor or compromise the host.

The security model is based on **separation of authority**:

- presentation may display;
- experiment execution may compute;
- verification may validate;
- proof qualification may promote formal evidence;
- provenance may identify and preserve evidence;
- AI may suggest;
- no lower-trust layer may silently acquire the authority of a higher-trust layer.

## 2. Trust zones

### Zone A — Browser / presentation

Examples:

- web canvas;
- coordinate/tile views;
- 2D/3D camera state;
- plots, reports, proof explorer;
- user interaction state.

Trust level: low.

Rules:

- browser state is untrusted input to the API;
- presentation-only state must not alter scientific evidence;
- all scientific mutations pass through typed server/core contracts;
- no client-side badge or field may create PASS/formal status.

### Zone B — Application/API orchestration

Examples:

- FastAPI endpoints;
- experiment/session handling;
- graph validation;
- module execution orchestration;
- persistence and export.

Trust level: medium.

Rules:

- validate schemas and types at every boundary;
- never trust client-provided evidence status;
- enforce authentication/authorization where multi-user access exists;
- enforce resource and upload limits;
- isolate long-running jobs from request handlers;
- use least-privilege service identities.

### Zone C — Scientific runtime

Examples:

- Python modules;
- C++ kernels;
- numerical solvers;
- certificate checkers.

Trust level: claim-specific.

Rules:

- each module exposes assumptions, inputs, outputs, limitations, and verifier contract;
- native code has independent tests and bounded interfaces;
- GPU is optional and backend choice is recorded;
- numerical success never implies formal proof.

### Zone D — Formal qualification

Examples:

- pinned Lean;
- pinned Mathlib;
- theorem metadata extraction;
- kernel axiom audit;
- exact-head attestation.

Trust level: highest mathematical evidence boundary.

Rules:

- isolate from untrusted browser requests and AI;
- use exact-current-head source;
- use pinned toolchain/dependencies;
- fail closed on unfinished proofs, unexpected axioms, metadata mismatch, source drift, or artifact mismatch;
- caches may accelerate but never substitute for exact-head validation.

### Zone E — Local AI / autonomous assistant

Examples:

- local LLM;
- hybrid neural component;
- Researcher/Autonomous modes.

Trust level: untrusted advisory.

Rules:

- AI output is never evidence;
- zero-contact mode has no Internet, cloud credentials, direct shell, or arbitrary host filesystem access;
- capabilities are explicit, mediated, bounded, and auditable;
- consequential source/canvas changes can require approval;
- the app must remain fully functional with AI disabled.

### Zone F — Plugins / third-party modules

Trust level: untrusted until explicitly promoted by policy.

Rules:

- manifest compatibility and trust metadata;
- transactional registration;
- future process isolation/capability permissions;
- no direct access to proof promotion authority;
- no silent access to secrets.

### Zone G — Provenance and evidence storage

Examples:

- local run bundles;
- OCI Object Storage;
- evidence ledger;
- signed attestations.

Trust level: integrity/provenance only.

Rules:

- preserve immutable/content-addressed identity;
- never equate signatures/hashes/log retention with mathematical correctness;
- missing archival must be visible.

## 2.1 Zero-egress scientific core and network brokers

The scientific worker should have no general Internet egress.

Network-enabled functionality is split into separate broker processes:

- **Collaboration broker** — may connect only to configured collaboration relay endpoints and exchange a fixed, bounded canvas-operation protocol.
- **Licensing broker** — may connect only to configured licensing/payment infrastructure and return signed license/quote state.

Neither broker may:

- load Python/JavaScript/Lean into the scientific worker;
- install packages/plugins;
- expose a shell;
- write arbitrary scientific workspace files;
- set trusted proof/evidence state.

Use Unix-domain sockets or another narrow local IPC boundary where practical. The scientific core should not receive broker credentials.

Browser policy should bundle application assets locally and use a restrictive CSP. The browser may connect to local CACE services, but should not fetch executable dependencies or scientific modules from third-party origins at runtime.

See `docs/OFFLINE_COLLABORATION_AND_LICENSING.md`.

## 2.2 Source-secrecy / anti-reverse-engineering gate

Customer-distributed artifacts are treated as hostile territory.

CACE uses a separate source-secrecy assurance dimension with fail-closed release gates covering classification, dependency boundaries, browser bundle hygiene, protected native-core packaging, encrypted assets, CPU/GPU buffer minimization, final artifact scanning, runtime integrity, and adversarial release testing.

The final customer artifact must be scanned by `scripts/check_release_secrecy.py` under `security/release_secrecy_policy.json`.

The highest-value theorem/proof machinery should remain off customer hardware whenever local execution does not require it. Local compilation/stripping/obfuscation raises extraction cost but does not make customer-controlled execution impossible to inspect.

See `docs/SOURCE_SECRECY_AND_ANTI_REVERSE_ENGINEERING.md`.

## 3. Protected assets

Protect at least:

- proof source and qualification inputs;
- claim registry and proof ledger;
- signing keys and deployment credentials;
- user experiments and unpublished research;
- datasets and evidence bundles;
- plugin/AI capability policy;
- production database/object storage;
- CI runner credentials and cloud tokens;
- exact source/artifact provenance.

## 4. Threat classes and required defenses

### Input and parser abuse

Defenses:

- typed schema validation;
- size/depth limits;
- path normalization;
- reject traversal and unsafe archive extraction;
- fuzz/property tests for parsers and serializers;
- bounded recursion and generated object counts.

### Web/API attacks

Defenses:

- HTTPS;
- secure cookies/session handling where applicable;
- CSRF protections when browser credentials are used;
- narrow CORS;
- restrictive CSP;
- request size/rate limits;
- output escaping;
- authentication/authorization checks;
- no secrets in frontend bundles.

### Supply-chain compromise

Defenses:

- pinned/locked dependencies;
- exact toolchain identities;
- checksums/signatures where available;
- SBOM for production releases where practical;
- dependency review and update testing;
- separate proof dependency pins from application convenience dependencies.

### Plugin compromise

Defenses:

- capability allowlists;
- versioned manifest contract;
- isolated process target for untrusted plugins;
- file/network/device permissions denied by default;
- bounded resources and timeouts.

### AI escape / excessive authority

Defenses:

- zero-contact sandbox;
- no network by default;
- no cloud credentials;
- capability broker instead of shell;
- explicit approved read/write roots;
- audit trail;
- human approval for high-impact actions.

### CI / runner compromise

Defenses:

- dedicated runner identities;
- no proof runner exposed as a general web worker;
- minimal repository/cloud permissions;
- durable external logs;
- exact commit checks;
- ephemeral working directories;
- persistent caches treated as untrusted acceleration and revalidated.

### Evidence/provenance tampering

Defenses:

- SHA-256 or identified hash algorithm;
- canonical manifests;
- append-only ledger;
- versioned object storage;
- signed attestations where enabled;
- independent mirror;
- exact commit/artifact binding.

## 5. Secrets and credentials

Secrets must never be committed.

Preferred handling:

- environment/service secret injection;
- cloud instance principals or narrowly scoped workload identities where practical;
- short-lived credentials;
- separate credentials for web app, object storage, deployment, and proof infrastructure;
- rotation and revocation procedures;
- no secret access from local AI sandbox or browser code.

## 6. Web deployment boundary

Recommended production shape:

`Browser -> HTTPS reverse proxy -> API -> job/runtime service -> durable storage`

Formal qualification is separate:

`controlled qualification request -> isolated proof runner -> exact source -> Lean/kernel audit -> content-addressed artifact -> provenance store`

The public API must not be able to execute arbitrary shell commands on the proof runner.

## 7. Failure behavior

Security and evidence failures fail closed within their scope.

Examples:

- missing verifier -> NOT_RUN, never PASS;
- invalid auth -> deny request;
- unavailable archival mirror -> archival/provenance failure, not theorem failure;
- plugin permission denial -> plugin failure, not host-policy bypass;
- AI sandbox violation -> terminate capability/session and preserve audit evidence;
- source drift after qualification -> formal promotion denied until requalified.

## 8. Security testing

Production candidates should include:

- unit/integration authorization tests;
- malformed schema/input tests;
- property-based tests;
- parser/API fuzzing;
- C++ ASan/UBSan where supported;
- dependency and secret scans;
- sandbox escape/adversarial tests;
- permission-negative tests;
- backup/restore tests;
- disaster recovery of evidence bundles;
- security review of deployment configuration.

## 9. Security does not change mathematical truth

Security protects execution and evidence integrity. It does not prove mathematics.

Likewise, a Lean theorem does not prove the web service is secure.

CACE must keep these assurance dimensions separate and expose both honestly.
