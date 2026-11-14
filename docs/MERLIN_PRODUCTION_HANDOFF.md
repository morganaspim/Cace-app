# Merlin + CACE Production Continuity Handoff

**Purpose:** durable, cross-chat and cross-agent project memory. Read this before making changes. This document is navigation and engineering context, not verification evidence or an authority grant.

**Last refreshed:** 2026-11-13 UTC  
**Canonical source:** the exact checked-out Git commit plus live GitHub state. This snapshot must be re-queried before acting.

## Standing instruction for every AI, agent, chat, and coding session

Do not ask the user to reconstruct context already preserved here. At the start of each session:

1. Read this file, `docs/CROSS_CHAT_HANDOFF.md`, `CACE_AGENT_BOOTSTRAP.json`, `docs/STATUS.md`, `docs/BUG_FLUSH_ARCHITECTURE.md`, and `formal/FAILURE_GUARDRAILS.md`.
2. Read the current branch, PR chain, workflow run, and exact source commit from GitHub. A handoff snapshot is not live state.
3. Read `docs/MERLIN_OCI_JOB_GATEWAY.md` and `docs/OCI_RUNNER_OPERATIONS.md` before dispatching or changing runner work.
4. Identify the highest-value safe next gate; continue without asking the user to repeat already preserved requirements.
5. For each newly discovered bug, add a defect-class entry, a deterministic regression/mutation test, and an early structural guard where feasible. Verify the detector itself with positive and negative controls.
6. Update this handoff whenever a material source, PR, runner, evidence, security, proof, or deployment state changes.
7. Never infer that a new AI, chat, model, agent, or memory system has inherited context unless it reads these repository files. This repository is the durable handoff surface; conversational memory is only a convenience.

## Project identity and scope

Merlin is the user's long-running research and engineering operating system project. It is not an election/voting project. The objective is a real, production-oriented system—not a mockup or a plan-only response.

Merlin's desired product:
- persistent chat and voice/agentic interface with a low-obstruction HUD;
- adaptive research canvas, branching investigations, evidence flow, and navigable knowledge graph;
- visible agent/council assignments and states (including Hermes, MCFC, Avrea, CACE, and skeptical review roles);
- mathematical discovery with inductive exploration, deductive proof, numerical experiments, counterexamples, Lean, and provenance;
- engineering workflows with FreeCAD/CAD, wiring/netlists, safety/thermal/manufacturability checks, simulation and ngspice;
- image/video generation and visual explanations;
- a headless internal Forge with commits, branches, virtual PRs, 3-way merges, conflict resolution, rollback, isolated CI, logs, and evidence receipts.

Merlin MVP comes first; then Merlin should help build and improve itself. The engineering plan should evolve from observed requirements and failures. Prefer ranked next actions and actual implementation on connected resources over speculative architecture alone.

## Canonical architecture and boundaries

- **Registry/API:** canonical project and artifact registry; universal artifact model; read-only project/artifact queries; immutable source identity and digest.
- **Knowledge graph:** typed entities/relations, research branches, claim provenance, evidence edges, and source hashes.
- **Hermes:** orchestration, decomposition, routing, idempotency, outbox acknowledgement, retries and durable job state.
- **MCFC:** virtual compute fabric, worker scheduling, resource budgets, execution leases, telemetry and bounded environments.
- **Avrea / OCI:** real runner execution; prefer existing approved Avrea/OCI capacity. Do not revive Cloudflare as a runtime or deploy target; the user previously removed/disabled it.
- **CACE:** independent verification of exact submitted artifact bytes and typed receipts. A hash string or AI assertion is not independent verification.
- **Capability registry:** explicit `configured`, `unavailable`, and `unqualified` states. Capability may grow; authority never expands automatically.
- **Gateway:** async streaming, cancellation, deadlines, concurrency limits and resource accounting.
- **Evidence:** source repository + exact commit, artifact digest, tool/version/environment, command/parameters, result, and independent verifier receipt. Keep engineering evidence distinct from formal proof.
- **Forge:** SQLite-backed commits/branches/PRs/event history, 3-way merge, conflicts, rebase/rollback, isolated headless CI, and explicit controlled merges. GitHub is a source mirror/control surface, not the intended primary user workflow.

## Security and approval invariants

- Fail closed when verification transport, trust material, capability, or resource limit is missing.
- No client- or AI-supplied claim can promote itself.
- No auto-promotion from CI success, numerical evidence, signatures, documentation, or chat agreement.
- Exact bytes must be submitted to independent CACE verification; the verifier must bind the receipt to those bytes.
- Leases, idempotency keys, preview diffs, approvals, heartbeats, resource limits, cancellation and append-only event history are required at execution boundaries.
- Keep signing keys and tokens out of Git, artifacts, logs, PR descriptions, and frontend code.
- Do not broaden IAM or runner sudo authority to make a workflow pass.
- Keep experimental research (including Titan encryption research) separate from production security claims and the general invention graph.
- A successful test, OCI run, or engineering EvidenceBundle is not a Lean theorem or canonical formal qualification.

## Current CACE branch and PR chain

Repository: `morganaspim/Cace-app`.

- Parent candidate: PR #101, branch `feat/merlin-continuum-oci-reproduction-20261112`, exact head at the last reviewed snapshot `57810a37fee14413ed8189e0f4a8995787c4aed0`.
- Guardrail child: PR #102, branch `fix/lean-proof-hole-guard-regex-20261113`, stacked on PR #101. It is a draft and must not be merged independently.
- Latest PR #102 head at this handoff: `a9b8a9c661c7271e40d8927c1622c67ced52ccdb`.
- PR #102 includes the corrected Lean proof-hole detector and mutation canaries plus F-031 in `formal/FAILURE_GUARDRAILS.md`.
- Do not merge either PR without reviewing the parent integration chain, exact base ancestry, checks, and explicit approval.

### Guardrail defect fixed

The previous test used doubled backslashes in regexes intended to match word boundaries, so ordinary `sorry` and `admit` tokens could evade the source-contract check. The repaired code compiles actual patterns `r"\\bsorry\\b"` and `r"\\badmit\\b"`, routes the source through a detector, and tests:
- reject `by sorry`;
- reject `by admit`;
- accept a valid proof token;
- accept `admitted_theorem` as an identifier (not a proof hole).

F-031 records fingerprint, root cause, permanent prevention and regression test. The test is a Python source-contract guard; it is not a Lean kernel check.

## Exact current validation state

- CACE collaboration validation run #654 succeeded on earlier code head `84b4dae2c725b86a094396f62ae614b4ac433fc5`. It validated the regex repair/canaries before the ledger-only follow-up commit.
- Latest-head run #655: GitHub run ID `43467350798`, exact head `a9b8a9c661c7271e40d8927c1622c67ced52ccdb`, conclusion **success**. Link: https://github.com/morganaspim/Cace-app/actions/runs/43467350798
- Job `validate` completed successfully on the self-hosted OCI lane. Exact-head checkout, repository-wide Actions serialization/policy, collaboration structure/lifecycle, read-only OCI runner inventory, read-only MCP protocol probe, pinned Python environment, collaboration + canonical formal-preflight pytest set, exact-byte CACE continuum EvidenceBundle construction, qualified-baseline ancestry check, engineering-only summary, and artifact upload all passed.
- Retained artifact: `cace-collaboration-validation`, artifact ID `14057784033`, 292,401 bytes, not expired at time of snapshot.
- Run #655 is **engineering-only validation**. It is not the exact-pin Lean compile of the new continuum module, not canonical proof qualification, not a signed attestation, and not promotion.
- Earlier independent CACE OCI validation run #653 (ID `43447334912`) reproduced the C++ continuum/simplicial smoke results and independent RP²/SNF audit on exact source commit `a55865e120346a37e8d8545ccf90154b5ad583ae`; it produced a 14-artifact engineering EvidenceBundle. Its attestation request was prepared but unsigned because no signer secret/endpoint and independently pinned signing trust were available. See prior run evidence before relying on any detail.
- Source repository: `Mannyspiro/expert-robot`, feature branch `feat/merlin-continuum-ir-stack-20261112`, PR #143 (draft at last snapshot). The CACE continuum candidate is quarantined; no root import or formal promotion implied.

## Immediate math and formal gates

1. Dispatch the exact-pin Lean preflight for `CACEFormal.ContinuumSimplexCore` from the CACE Actions UI: https://github.com/morganaspim/Cace-app/actions/workflows/cace-batch-exact-pin-lean-preflight.yml
2. Use Lean `leanprover/lean4:v4.32.1` and exact Mathlib commit `520045ab14e26149ee970e2e617ca04b09bde5d6`; do not update pins to obtain a green result.
3. `prewarm_mathlib_cache=false` unless an explicit cache-refresh decision is made.
4. Preserve standalone quarantine. A standalone compile is not audited-root qualification; root promotion requires separate audited-root compile, kernel axiom audit, theorem metadata, proof-contract checks, exact environment and canonical qualification.
5. Independently reproduce the RP² and Smith Normal Form results; keep the pure-Python audit independent from C++ implementation. Validate representative homology classes, not just cycle closure. Preserve endpoint-gluing constraints in continuum IR and filtration provenance.
6. Keep the protected OCI gateway/signer chain separate. The distinct fixed-profile OCI push run, protected orchestrator validation, signer configuration, independently pinned trust material, and CACE signed receipt are still outstanding. No fabricated signature or self-reported SHA.
7. Append independently verified evidence to Hermes candidate lineage and canonical registry only after CACE validates exact bytes. Promotion remains a separate explicit approval.

## Bug-to-guardrail policy

CACE already has 30 defect classes F-001 through F-030 and this PR adds F-031. Reuse, do not duplicate, existing mechanisms:
- `formal/FAILURE_GUARDRAILS.md`
- `scripts/cace_proof_guardrails.py`
- `scripts/check_cace_known_failure_regressions.py`
- `scripts/check_cace_workflow_guardrails.py`
- `formal/cace_formal/proof_guardrails.json`
- `docs/BUG_FLUSH_ARCHITECTURE.md`

Required lifecycle for every confirmed defect:
1. Preserve exact failing input, source commit, toolchain, environment, logs and digests.
2. Assign a stable defect-family fingerprint and ledger ID.
3. Create a deterministic minimal reproducer.
4. Sweep sibling instances and adjacent trust boundaries.
5. Fix root cause without weakening scientific/proof/security scope.
6. Add regression tests and mutation/property controls that prove the detector catches the defect.
7. Add the earliest practical static/preflight guard and make it fail closed.
8. Demonstrate vulnerable behavior fails and repaired behavior passes.
9. Retain exact-head diagnostics and link run/commit/artifact digests.
10. Reopen the defect class if it recurs; add the new reproducer rather than silently editing history.

## Runner and compute setup

The currently approved execution target is the existing OCI self-hosted runner lane labelled `self-hosted`, `cace`, `oci`, `aarch64`; the known runner identity from prior successful runs is `cace-oci-a1`. The collaboration workflow now records a bounded, read-only runner inventory and MCP health probe as part of the validation artifact.

Read `docs/OCI_RUNNER_OPERATIONS.md` before any runner action. Key points:
- preserve the existing OCI instance, Actions runner registration, persistent Lean/Mathlib caches and evidence;
- use the existing service and least-privilege instance principal;
- never copy the archived broad-sudo provisioning pattern;
- never expose the loopback MCP endpoint publicly;
- use one-hour GitHub registration tokens only interactively and never log/store them;
- do not reinstall, re-register, resize, clean caches, delete files, or expand IAM without an explicit approved plan;
- historical gateway documentation reported roughly 0.5 GiB free on a 30 GiB root filesystem. Treat disk headroom as a hard gate and re-measure before any heavy compile or package installation. This number is historical, not a current measurement.
- Avrea minutes are a finite budget; check the current allowance before scheduling broad work.

## Broader Merlin technical priorities

- Consolidate registry + universal artifacts + knowledge graph + provenance + outbox + mathematical modules into one canonical implementation.
- Add canonical capability registry and async streaming gateway with bounded concurrency/deadlines/cancellation.
- Connect Hermes outbox acknowledgements and Avrea dispatch with explicit approval, resource limits, result collection and CACE verification.
- Implement MCFC worker/resource scheduler with leases, budgets, telemetry and deterministic receipts.
- Build the internal Forge with immutable event history, virtual PRs, merge previews/conflict checks, isolated CI and rollback.
- Implement engineering IR, FreeCAD importer, netlist/wiring graph, electrical safety/thermal/manufacturability checks and real ngspice adapter with version/input/output/resource receipts.
- Keep math discovery path structured: Ideonomy hypothesis -> typed claim/assumptions/falsifiability -> numerical experiment/counterexample -> supplied Lean source -> pinned compile -> CACE exact-byte verification. No generated `sorry` scaffolds.
- Keep provider/model qualification measured on held-out tasks; do not let an AI grade its own evidence.

## Handoff maintenance

At the end of each substantive session, update:
- this file with exact current branch/commit/PR/run/artifact and next gate;
- `docs/CROSS_CHAT_HANDOFF.md` for the standing continuity rule;
- `CACE_AGENT_BOOTSTRAP.json` so every AI entrypoint discovers this file and runner operations;
- `formal/FAILURE_GUARDRAILS.md` for new confirmed defect classes;
- `docs/STATUS.md` only when product/qualification state changes (do not call this PR success production readiness).

This handoff is intended to survive chat resets, model changes and agent handoffs because the repository itself carries the context.


## Detailed source and evidence lineage (retain exact identities)

### Expert Robot source candidate

- Repository: `Mannyspiro/expert-robot`.
- Feature branch: `feat/merlin-continuum-ir-stack-20261112`.
- PR #143: draft at last known snapshot.
- Source commit used for the independent C++/Python audit: `a55865e120346a37e8d8545ccf90154b5ad583ae`.
- Source CI run #3846 / run ID `43447003376`: success; Learning run #3846 companion ID `43447003328`: success.
- Source diagnostics artifact ID `14049215558`, SHA-256 `a42e036b23b48b6ce0e807c4eaad239a50362c5ac1cd0e5b2c996105f4edb045`.
- C++/test source binding in CACE pins header Git blob `77d806965d1b4b285858221aab88d78e53a54597` and test blob `1469edd1a3624547742c3342253a142c848a5048`.
- Source binding manifest records the exact source commit, header/test blobs and validation run. Never replace this with an unverified user-supplied SHA.

### CACE independent reproduction run #653

- CACE PR #101 head at the run: `57810a37fee14413ed8189e0f4a8995787c4aed0`.
- Source repo/commit: `Mannyspiro/expert-robot` / `a55865e120346a37e8d8545ccf90154b5ad583ae`.
- CACE workflow run #653 / ID `43447334912`, success; OCI runner identity `cace-oci-a1`, execution ID `43447334912.1.validate`.
- Strict-warning C++20 compile/smoke results: `continuum_simplex_smoke.cpp` PASS; `simplicial_complex_smoke.cpp` PASS with persistence input/output SHA-256 receipts.
- Independent Python/Bareiss/tree-collapse reference: RP² integral homology H0=Z, H1=Z/2, H2=0; mod-2 Betti numbers (1,1,1); Smith Normal Form invariant factors `[1,1,1,1,1,1,1,1,1,2]`; five SNF fixtures validated.
- EvidenceBundle: 14 artifacts; artifact ID `14048596444`; ZIP SHA-256 `66f8c90be9ee37c9b61c65d2777435646c6d6d109eb92c49b66dd260bd7e70b0`.
- Independently checked bundle ZIP digest, 14 base64 payload hashes/sizes, EvidenceBundle SHA-256 `701fd6563223bcb0cf280185e42359dcdbfd7bfae38ac70ec534bae1b83047c6`, Merkle root `0d67b1ec2ff1cf273f0d4d7f61c8572dbaf7af2a65e48e1516ef465d4878afeb`, candidate digest `1cd2556161d611aa7ca2809f6e103409eab24269907d3283d935851e0b268f1e`, persistence envelope digest `6440f5150a09b9bb42911e1a55b93a256dd1bf90d21c71a90be7c2e7fdd1b46c`, evaluator receipt SHA-256 `7fa1fe1b8452195489ad2ea7632e0358543cc80d5b03b8ca7384605b5f73a745`, benchmark manifest SHA-256 `f29ab282fdee21f50d94482b51d356c8859782ad68cad479307186a0fbe46d02`.
- Classification: `ENGINEERING_VERIFIED`; `proof_implication=none`; `authority=verification-only`.
- Attestation state: `prepared_not_signed`; signature null; signer blocker was no exposed secret access, writable signer endpoint, or independently pinned signing key.
- This run does not prove the new Lean module, formal qualification, or production readiness.

### Lean and protected signer gates

- Exact-pin preflight workflow on `main`: `.github/workflows/cace-batch-exact-pin-lean-preflight.yml`.
- Workflow dispatch inputs include target module list and `prewarm_mathlib_cache` default false.
- Exact toolchain `leanprover/lean4:v4.32.1`; exact Mathlib commit `520045ab14e26149ee970e2e617ca04b09bde5d6`; target `CACEFormal.ContinuumSimplexCore`.
- The GitHub connector does not provide workflow_dispatch. A user/owner with Actions UI access must dispatch the workflow; do not claim it was run unless a new run ID and exact head are observed.
- Protected orchestrator validator exists on the PR #101 feature branch at `.github/workflows/merlin-cace-protected-orchestrator.yml`. It checks a successful fixed-profile OCI push run, exactly one successful `run-approved-profile` job on `cace-oci-a1`, required steps, and a retained SHA-256-bound receipt artifact. It is not yet on main.
- The protected signer workflow, external signer configuration and independently pinned trust material remain outstanding. A successful engineering workflow is not the distinct protected orchestrator run.
- Keep signing, verification, and promotion as separate transitions. Do not store signer keys in the repository or treat the OCI host's local key as an independent external signer.

### Related formal runtime constraints

- Existing CACE adapter constructor requires `verify_transport`, `registry`, `outbox`, optional `graph`; fail closed if verification transport is unconfigured.
- Hermes must route eligible/ineligible/ambiguous/malformed/rejected claims distinctly. Non-eligible claims must not reach Lean.
- Lean source must not contain `sorry` or `admit`; do not generate a fake proof scaffold.
- Every compiler receipt should bind exact source digest, toolchain, Mathlib lock/commit, command, exit status, stdout/stderr and environment.
- Numerical receipts should bind seed, precision, solver/version, parameters, environment, runtime and output digest.
- Counterexample receipts should bind domain/bounds, method, seed and termination result.
- CACE independently verifies the exact artifact bytes; Hermes stores the result with idempotency/outbox semantics.

## 2026-11-13 math guardrail continuation

- PR #102 remains OPEN and DRAFT, stacked on PR #101; do not merge this branch independently.
- The original F-031 regex fix remains in place. The shared `scripts/check_lean_source_sanity.py` scanner now additionally detects whole-token `sorry`/`admit` in Lean code after masking line comments, nested block comments, and strings.
- `.github/workflows/cace-batch-exact-pin-lean-preflight.yml` now scans the complete `formal/cace_formal` tree before target compilation, while retaining per-batch-target scans.
- `tests/test_lean_source_sanity.py` includes explicit proof-hole positive/negative fixtures. A fixture-escaping issue was corrected in commit `f66eaa63c5480bc49db2d377019087d4e1643475`; do not treat earlier mutation-test CI attempts as validating that final test text.
- Scanner implementation exact head `dca948e89c8153693b287da8c8c31caa84a568eb` passed collaboration validation run `43469516682` and Lean Source Sanity run `43469517086`. Both are source-guard validation, not Lean kernel compilation.
- Earlier full collaboration validation run `43468823050` passed on exact commit `1739266a2a22fde3c2fbae07f3ec232027cf07fb`, including OCI inventory, read-only MCP probe, tests, exact-byte EvidenceBundle build and artifact upload. It predates the new scanner extension.
- Exact current branch head must be re-queried after each commit. The final multiline fixture commit and subsequent docs commits require a fresh exact-head CI run; recent concurrent Actions runs were cancelled by the repository-wide serialization policy.
- Next math gate: obtain a successful exact-head scanner + collaboration run; then run the exact pinned Lean standalone compile for `CACEFormal.ContinuumSimplexCore` under Lean `v4.32.1` / Mathlib `520045ab14e26149ee970e2e617ca04b09bde5d6`. Workflow dispatch is not exposed by the connected GitHub action set; do not claim compilation until a run ID is observed.
- Preserve quarantine: no import into `CACEFormal.lean`, no promotion, no signing, and no proof-qualification claim until standalone compile, audited-root compile, kernel axiom audit, metadata/proof-contract checks and independent exact-byte CACE verification have passed.


## 2026-11-13 production Merlin artifact-lineage continuation

Source implementation is being developed in [Expert Robot PR #144](https://github.com/Mannyspiro/expert-robot/pull/144), stacked on Expert Robot PR #143. Live source branch: `feat/merlin-artifact-version-lineage-20261113`; latest observed head: `7593b782d688132b206fc16f83ddf131b919a496`. PR #144 remains OPEN/DRAFT and unmerged.

The source branch extends the existing canonical `MerlinRegistry` with append-only per-project/per-logical-path artifact versions and strict `merlin-artifact-ref/1` identities. The reference binds project ID, normalized logical path, chronological version and SHA-256. Resolution re-hashes exact bytes and checks size; historical versions remain resolvable. Currentness is based on version identity, not digest equality, including the A -> B -> A reversion case.

Artifact references have been propagated source-side through:
- research evidence results, graph node metadata and graph-edge provenance (graph identity includes version);
- `merlin-research-task/2` dispatch envelopes;
- Hermes input context and `merlin-hermes-task-result/2` receipts;
- the production Hermes runtime's injected canonical registry resolver, which revalidates input/output references;
- Avrea dispatch receipts and exact-byte input transfer, capped at 25 MiB per artifact / 50 MiB aggregate;
- Avrea collected output receipts and durable outbox events.

The source branch adds regressions for historical versions/reversions, tampered blobs, Hermes reference validation, missing-validator fail-closed behavior, Avrea input resolution and exact-byte transfer. Exact current-head native CI run `43534991502` and unified platform run `43534991526` were pending/queued at the latest live check. Earlier native CI passed on prior commits but does not validate the latest head. Do not claim the unified suite passed until a completed success for the exact current head is observed.

Critical remaining boundary: CACE's actual signed EvidenceBundle contract has not yet been updated to include the complete artifact reference (especially chronological version) in its signed statement and independent verification. Source-side digest checks are not a substitute. The next coordinated change must update the CACE verifier/signer producer and Merlin adapter together, require exact reference equality, re-resolve the referenced bytes independently, and retain pinned trust verification. Until then, end-to-end CACE artifact-version verification is NOT COMPLETE.

PR #144 has not changed any runner host, IAM, credentials, signer keys, deployment, or production configuration. It grants no promotion authority. Keep PR #144 draft and stacked; do not merge it independently. Keep signing, verification and promotion as distinct transitions.


## 2026-11-14 live continuation: artifact lineage CI and CACE integration boundary

Live recheck of Expert Robot PR #144:
- PR #144 remains OPEN/DRAFT, stacked on PR #143, head `7593b782d688132b206fc16f83ddf131b919a496`.
- Exact-head native CI run [43534991502](https://github.com/Mannyspiro/expert-robot/actions/runs/43534991502) completed SUCCESS on that exact SHA.
- Exact-head unified platform run [43534991526](https://github.com/Mannyspiro/expert-robot/actions/runs/43534991526) completed CANCELLED, not success. Do not claim unified integration acceptance.
- No merge, deployment, runner-host mutation, IAM change, credential change, signer configuration or promotion occurred.

### CACE implementation inspection (current main snapshot)

The previously assumed path `ops/oci_mcp/merlin_rsi_verifier.py` is not present in the current `morganaspim/Cace-app` main tree. Do not build against that stale path or assume the OCI MCP server is the signer.

Observed existing primitives:
- `cace_studio/core/attestation.py` implements canonical domain-separated Ed25519 signed statements. `AttestationStatement.bindings` is included in the signed canonical payload.
- `cace_studio/attest_cli.py` currently constructs only `qualified_commit` and `proof_artifact_sha256` bindings in its sign command. It has no artifact-ref input option.
- `verify_attestation` cryptographically checks the embedded public key/signature and key-id consistency. That alone does not establish trust in the embedded key; the consumer must compare the key identity against independently pinned trust material.
- `cace_studio/core/evidence_ledger.py` and `schema/evidence-bundle-v1.schema.json` define a manifest/Merkle bundle with artifact digest, size, role, media type, path and metadata. The bundle manifest does not itself provide a canonical Merlin registry resolver or independently fetch the bytes behind a versioned artifact reference.
- `ops/oci_mcp/server.py` is a narrow OCI operational control plane. Its documented tools cover runtime status, logs, instance/VNIC/NSG reads and explicitly gated network/service operations; it does not expose a Merlin artifact verifier or signing endpoint.

### Correct CACE integration design (do not skip the missing boundary)

The next CACE change must be a coordinated verifier/producer contract, not merely adding a free-form binding:
1. Define a strict versioned request schema that requires the complete `merlin-artifact-ref/1` tuple: project ID, logical path, chronological version and SHA-256, plus source repository/commit and artifact/tool identity.
2. Require CACE to independently resolve the project/path/version in the canonical registry and retrieve the exact bytes; re-hash bytes and verify size against registry metadata. Reject stale/missing/malformed references and all mismatches.
3. Bind the complete reference and the independent-resolution result into the EvidenceBundle and signed statement. Do not accept caller-supplied digest-only claims as independent resolution.
4. Add a consumer verifier that checks exact expected bindings and compares the signing key ID against independently pinned trust material; embedded-key self-verification is insufficient.
5. Add mutation tests for version/path/project/digest substitution, missing registry resolution, byte/size mismatch, signature mutation and trust-key substitution.
6. Keep `proof_effect: none`; signed integrity/provenance is not theorem proof, qualification, approval or promotion.

No signer endpoint or independently pinned external trust configuration was discovered in this inspection. Do not generate a production key, configure a host key, expose a new endpoint, change secrets/IAM, or claim signed end-to-end verification without the separately approved external signer and trust setup.

### Immediate next gates

1. Re-run the exact-head unified platform workflow for PR #144 and retain its full logs/artifacts; inspect cancellation cause before retrying.
2. Implement the strict CACE artifact-ref resolver/attestation request path against the actual canonical registry interface; first identify the registry transport contract rather than inventing an endpoint.
3. Extend the Merlin CACE HTTP adapter to send the full ref and validate the signed response against independently pinned trust.
4. Persist the verified receipt against the same ArtifactRef/version in the existing registry/event graph/outbox; do not create a parallel receipt store.
5. Add lineage/fault-injection coverage: concurrent writes, interrupted blob writes, restart, duplicate outbox delivery, backup/restore and orphan blob handling.
6. Keep PR #144 and the CACE PR chain draft/stacked until exact-head validation and integration review; no independent merge or promotion.



## 2026-11-14 exact-head continuation: unified-suite failures and repair

Expert Robot PR #144 has advanced to head `67013dd151b6a3c5839bec72d6f94ff327c16a98`. The prior head `7593b782d688132b206fc16f83ddf131b919a496` passed native CI (#43534991502), but its unified suite (#43534991526) was cancelled after its test step reported **210 passed / 10 failed**. The retained log was reviewed. The failure set comprised:
- over-escaped ngspice version parser;
- ambiguous CACE proof-effect validation error;
- stale CACE trusted-key fixture shape;
- Hermes missing-validator test accidentally using a helper that injected a permissive validator;
- missing app/EventStore imports in Hermes runtime tests;
- case-sensitive urllib request-header assertion;
- Forge conflict test not satisfying required independent-check gates;
- merge-commit rebase test not advancing its target branch;
- stale Forge API README expectation.

Regression repairs are committed in source commits `3f37e01579bb2edd691a749f6350b39ff1d8fa4a` and `67013dd151b6a3c5839bec72d6f94ff327c16a98`. The ngspice version parser now has explicit positive/negative banner fixtures. Several failures were test-fixture/expectation errors exposing stale assumptions; the ngspice parser and CACE error specificity were implementation fixes. Re-run all tests on the new exact head before classifying any residual failures.

Fresh exact-head workflows on `67013dd151b6a3c5839bec72d6f94ff327c16a98`:
- Native CI run `43544593135`: PENDING at last observation.
- Unified platform run `43544593226`: IN_PROGRESS at last observation.
No pass is claimed yet.

Keep PR #144 OPEN/DRAFT and stacked on PR #143. The CACE artifact-reference/signing boundary remains unimplemented; the corrected CACE repository inspection and strict next-gate design are in the preceding section of this handoff. No runner, IAM, credential, signer, deployment or promotion change occurred.


Latest source follow-up: the first repair commit's unified run #43544593226 reached 220 passed / 1 failed; the remaining failure was only a newline-escaping error in the revised README assertion. Source commit `53d0f18d0f0cd15acd15dae2f8a19ced0509a5db` removed that brittle newline check. Fresh exact-head workflows on this commit are native CI #43544767097 and unified platform #43544767303, both IN_PROGRESS at last observation. Earlier head `67013dd151b6a3c5839bec72d6f94ff327c16a98` native CI #43544593135 passed, but unified #43544593226 failed; do not transfer its native success to the latest head.


## 2026-11-14 authenticated artifact-resolution API implementation

Expert Robot PR #144 now contains an initial read-only resolver boundary on source head `57e74bae65237e86d6efbcde3dab0e518e5b8b8d`:
- `MerlinRegistry.read_artifact_ref` resolves an exact historical version, enforces a hard 25 MiB per-artifact ceiling, and rechecks the returned byte length and SHA-256.
- `POST /api/artifacts/resolve` accepts only `merlin-artifact-resolution-request/1` with the complete ArtifactRef; returns `merlin-artifact-resolution/2` with the immutable ref, resolution metadata and base64 bytes.
- The route requires a separate `MERLIN_ARTIFACT_READ_TOKEN` (minimum 32 ASCII characters), compares bearer tokens in constant time, and fails closed if token or canonical registry is absent. It is read-only.
- API tests cover historical-version retrieval after the path advances, invalid/unconfigured token behavior, forged digest rejection, byte ceilings and strict request schema. These tests are included in the existing unified platform test invocation.

Fresh workflows triggered on the latest source head include unified run `43545218628` (queued at last check); native CI and related integration workflows are also queued. Exact-head success is NOT YET CONFIRMED. No production token was created, no host or deployment configuration changed, and no external endpoint has been exposed/configured.

CACE still must consume this API through a configured authenticated transport, independently decode and re-hash exact bytes, bind the full project/path/version/digest reference into EvidenceBundle and signed statement, and verify the signature against independently pinned trust. The Merlin endpoint is a prerequisite boundary, not an independent CACE receipt. Keep end-to-end verification NOT COMPLETE until all these pieces pass together.


Latest integration note: the resolver endpoint work on Expert Robot PR #144 surfaced a compileall-only defect in `tests/test_research_dispatch.py`: the helper passed `artifact_ref_validator` twice. The duplicate was removed and `tests/test_research_dispatch.py` was added to the unified platform test command in commit `d64a932d6cae3ba1fdc5250cee494f7351c58d42`. The previous hosted-evidence run #43545218684 had all 31 API tests pass but failed compileall on that duplicate keyword. On the latest source head `d64a932d6cae3ba1fdc5250cee494f7351c58d42`, native CI #43545472615 is IN_PROGRESS and unified platform #43545472669 is QUEUED. No exact-head pass is claimed.


## CACE artifact-reference integration inspection (2026-11-14)

Inspected the actual CACE signer/verifier and OCI MCP registration rather than assuming the RSI path was a generic artifact API:
- `ops/oci_mcp/merlin_rsi_verifier.py::attest_merlin_rsi_bundle` already verifies exact EvidenceBundle bytes through CACE core and can sign an `artifact-integrity` statement with `proof_effect=none` / `authority=verification-only`. It accepts a caller-supplied expected-bindings mapping and candidate ID but currently does not enforce Merlin's `merlin-artifact-ref/1` structure.
- `verify_merlin_rsi_attestation` is deliberately RSI-specific: it requires the exact RSI binding schema and `purpose=independent-reproduction`. Do not reuse it as a generic artifact-reference verifier.
- `ops/oci_mcp/server.py` registers the bundle attestor as an OCI MCP tool behind `CACE_OCI_MCP_ALLOW_MERLIN_RSI_SIGNING`; the private key path is `/var/lib/cace-oci-mcp/keys/merlin-rsi-attestor-ed25519.pem`. The server tool accepts bundle payload, expected claim ID, expected bindings and exact artifact bytes. No signing feature flag or key was configured/changed during this inspection.
- `_approved_keys` requires a digest-pinned trust-store document with active CACE verifier key IDs. The generic verification function still needs a distinct contract for artifact-integrity statements that validates the full ArtifactRef and does not confuse integrity attestation with RSI reproduction.

Next CACE implementation should add a distinct Merlin ArtifactRef attestation/verification contract, not broaden the RSI verifier: validate exact `merlin-artifact-ref/1` fields (project, normalized logical path, positive chronological version, SHA-256); bind the whole ref plus source repo/commit and artifact schema/kind in the signed statement; require exactly corresponding EvidenceBundle artifact(s); independently resolve bytes from the authenticated Merlin read-only resolver and compare returned ref, declared size and SHA-256; then call CACE core `verify_bundle` and sign purpose `artifact-integrity`. The matching verifier must validate signature against independently digest-pinned CACE trust material and exact bindings. Mutation tests must cover ref/path/version/digest substitution, stale version, byte mismatch, wrong signer, trust-store digest/key substitution, and RSI-vs-integrity purpose confusion. Keep proof effect none and promotion authority absent.

At this point this is a reviewed implementation design, not an implemented or configured end-to-end connection. The Merlin source endpoint exists in PR #144 but no production URL/token has been provisioned; CACE signer feature flag/key/trust configuration remains unverified. No credentials, secrets, host services, or deployments were modified.


## 2026-11-14 exact-head Merlin regression continuation

Expert Robot PR #144 remains OPEN/DRAFT and stacked on PR #143. Exact source head beaf612da6d049518fda6f67b3ebb8cb2e3d9de9 fixes the two remaining regressions observed on preceding exact head 2cb255baf086d41aa02eb06658d5ac7210572529: the Forge HTTP fixture now asserts the actual Expert Robot README identity, and the merge-commit rebase fixture advances protected main only through the explicit test-only allow_protected=True setup hook. Production protected-branch enforcement is unchanged.

On preceding head 2cb255b, native CI #3869 succeeded, unified run #504 completed with 229 passed / 2 failed. Fresh exact-head native CI #3870 and unified platform run #505 are IN_PROGRESS on beaf612d; do not claim success until both complete on that exact SHA. Related voice/HUD qualification run #506 and representation spectrum run #622 were cancelled; do not transfer earlier results.

Latest exact source state and run links:
- Commit: https://github.com/Mannyspiro/expert-robot/commit/beaf612da6d049518fda6f67b3ebb8cb2e3d9de9
- Native CI: https://github.com/Mannyspiro/expert-robot/actions/runs/43600074262
- Unified platform: https://github.com/Mannyspiro/expert-robot/actions/runs/43600074355

Next: inspect exact-head #505 logs if it fails; otherwise verify the artifact and commit binding from its uploaded evidence. Continue CACE ArtifactRef implementation only after re-reading actual source paths at current CACE branch head. The earlier inspected ops/oci_mcp/merlin_rsi_verifier.py and ops/oci_mcp/server.py locations were described in the handoff, but a fresh fetch against the currently selected CACE PR branch returned 404; re-discover exact current paths before editing. Do not infer the path exists from an older snapshot. No production signer, trust key, secret, feature flag, host, IAM or endpoint configuration was changed.


## 2026-11-14 CACE ArtifactRef implementation discovery and Merlin CI closure

The CACE implementation path was re-verified on this branch: `ops/oci_mcp/merlin_rsi_verifier.py` exists (blob `99179a7f92f41bc9b89669813b59d869b0062131`) and `ops/oci_mcp/server.py` exists (blob `95edf8fdc3fd78263c4179b54f5989235184ba70`). The verifier currently exposes generic `attest_merlin_rsi_bundle` signing `purpose=artifact-integrity` with caller-provided bindings, but it does not enforce a strict Merlin ArtifactRef. `verify_merlin_rsi_attestation` remains RSI-specific: exact RSI bindings and `purpose=independent-reproduction`. It must not be reused as the generic ArtifactRef verifier. The server registers RSI-specific tool names and gates them behind `CACE_OCI_MCP_ALLOW_MERLIN_RSI_SIGNING`; there is not yet a distinct ArtifactRef tool or independently resolving CACE transport in the inspected module.

The Merlin resolver response contract was verified from Expert Robot exact passing source head `beaf612da6d049518fda6f67b3ebb8cb2e3d9de9`: POST `/api/artifacts/resolve` request is exactly `{schema: merlin-artifact-resolution-request/1, artifact_ref}` with bearer auth. Successful response has `schema=merlin-artifact-resolution/2`, `artifact_ref`, `resolution`, `media_type`, `size_bytes`, `content_sha256`, `content_b64`, and `authority=read_only_artifact_bytes`. The nested registry resolution includes schema `merlin-artifact-resolution/1`, exact artifact_ref, media_type, size_bytes, previous_digest, created_at, is_current and verified=true. CACE must independently decode the base64 bytes, enforce canonical encoding, compare returned and requested references exactly, compare size and SHA-256, then verify the exact matching EvidenceBundle artifact and sign the whole binding set.

Expert Robot PR #144 exact head `beaf612da6d049518fda6f67b3ebb8cb2e3d9de9` now has both required gates SUCCESS: native CI #3870 / run `43600074262` and unified platform #505 / run `43600074355`. Unified evidence artifact ID `14115542251`, SHA-256 `ce920daec192e3c69b8eb748525cff773d6f74566b015651f8d4225381c6e375`. PR #144 remains OPEN/DRAFT and stacked on #143; no merge or production deployment is implied. This closes the source-side exact-head regression gate only.

Next CACE code work: create a distinct `merlin-artifact-integrity` contract and verifier, not an extension of the RSI reproduction schema. Bind the entire ArtifactRef plus source repo/commit and artifact ID/kind/schema in both EvidenceBundle and signed statement; require exact artifact identity and no extra/unmatched bundle bytes; use an injected authenticated resolver transport with configured endpoint/token only at runtime; reject stale/substituted/mismatched response; verify signatures against independently digest-pinned CACE trust; keep `proof_effect=none` and authority `verification-only`. Add mutation tests for every reference field, historical version substitution, resolver response schema/bytes/size/digest, EvidenceBundle artifact identity, wrong signer/trust digest, and purpose confusion. Do not create a key, populate trust, enable feature flags, configure URL/token, or alter OCI host/IAM/service state as part of code-only work.


## 2026-11-14 CACE ArtifactRef implementation and exact-head gate

Current CACE PR #102 head at this handoff: `7082e600105a41982e066d3bd9f39a8b49b3cd6f` (OPEN/DRAFT, still stacked on its paired continuum/OCI parent). This supersedes older statements above that ArtifactRef code was not yet implemented.

Implemented on the branch:
- `ops/oci_mcp/merlin_artifact_ref.py`: separate ArtifactRef attestor/verifier; strict full reference validation; authenticated resolver injection; canonical base64 and independent byte size/SHA-256 checks; full source repo/commit + artifact identity binding; exact one-artifact EvidenceBundle requirement; manifest path/role/schema/digest binding; pinned CACE trust verification; 30-day signature freshness window; `proof_effect=none`, verification-only authority.
- `ops/oci_mcp/server.py`: separate MCP tools for key initialization, attestation, verification and capability readiness. MCP server object is initialized before decorators register tools. Resolver transport requires HTTPS, bearer token, exact resolver path and rejects redirects.
- Separate ArtifactRef signing key path: `/var/lib/cace-oci-mcp/keys/merlin-artifact-ref-attestor-ed25519.pem`; feature flag: `CACE_OCI_MCP_ALLOW_MERLIN_ARTIFACT_REF`. These remain disabled/unprovisioned unless an operator configures them.
- `tests/test_merlin_artifact_ref.py`: reference-field substitution, stale/unverified resolution, canonical base64, digest/authority checks, full manifest binding, extra artifact rejection, and real CACE Ed25519 attestation→independent verification round trip with digest-pinned trust. The exact-head collaboration workflow now explicitly runs this test module.

Exact-head CI on `7082e600105a41982e066d3bd9f39a8b49b3cd6f`:
- Collaboration validation run #43600934614: SUCCESS — https://github.com/morganaspim/Cace-app/actions/runs/43600934614
- Lean Source Sanity run #43600934550: SUCCESS — https://github.com/morganaspim/Cace-app/actions/runs/43600934550
- Retained collaboration evidence artifact ID `14116262399`, SHA-256 `44e9263308b1660be4c5bf5ecd982f36995f8421f3e733ca3294fb9cafce47b2`.

Merlin resolver contract was independently compared with Expert Robot source `python/merlin/app.py` at exact passing head `beaf612da6d049518fda6f67b3ebb8cb2e3d9de9`: request schema/path/auth and successful response fields match the CACE transport. This is source-contract verification only; no live authenticated request was made because production endpoint/token are not provisioned.

Remaining gates (do not mark production qualified):
1. Provision the dedicated resolver URL/token, separate signer key and independently pinned trust store on the protected OCI host; keep feature flag disabled until custody is reviewed.
2. Run the protected signer initialization and verify key ID/public key against independently controlled trust material.
3. Execute a real historical ArtifactRef resolve→CACE attest→separate verifier round trip using exact Merlin bytes and a retained signed receipt.
4. Run a distinct protected orchestrator workflow on `main` linked to the exact successful OCI execution. Existing orchestrator workflow is manual-dispatch and main-only; no such run is evidenced yet.
5. Run the exact-pin Lean workflow on the intended formal target and record toolchain `leanprover/lean4:v4.32.1`, mathlib commit `520045ab14e26149ee970e2e617ca04b09bde5d6`, source SHA, stdout/stderr, exit status and independent CACE receipt. No new exact-pin kernel compilation result was produced by the ArtifactRef CI runs.
6. Independently reproduce RP²/SNF and expand persistence representatives/interacting cycles, then bind those results to the same exact source and evidence chain.

No production secret, signing key, trust store, feature flag, resolver deployment, OCI host/IAM/service state or workflow-dispatch run was changed/created by this code-only work. PR #102 remains OPEN/DRAFT; do not merge independently or infer deployment.


## 2026-11-14 ArtifactRef hardening: latest exact code head

Latest CACE code head: `ab6c146da6b990956fb64a53f78adee58abec69c`.
- Collaboration validation #43601156993: SUCCESS — https://github.com/morganaspim/Cace-app/actions/runs/43601156993
- This exact-head test command includes `tests/test_merlin_artifact_ref.py`; it passed the resolver mutation cases, full CACE Ed25519 sign/verify round trip, duplicate trust-key rejection and AST regression guarding MCP server initialization before tool registration.
- Evidence artifact ID `14115733300`, SHA-256 `1a789b77b7ce40febd2a00615cd1f4a05c04108dc872847df76a7cbcce99b87e`.
- Lean Source Sanity on earlier code head `7082e600105a41982e066d3bd9f39a8b49b3cd6f` passed as run #43600934550. No Lean source changed after that head; the newer Lean Source Sanity attempt on ab6c was cancelled before a job began. Do not call it a pass on ab6c.

Exact-pin math target clarification: the current CACE repository contains `formal/cace_formal/CACEFormal/ContinuumSimplexCore.lean`, which is explicitly listed in `proof_guardrails.json` as `quarantined_root_imports`. The correct targeted preflight invocation is workflow `CACE Exact-Pin Lean Preflight` with module `CACEFormal/ContinuumSimplexCore.lean`, `compile_root=false`, and `prewarm_mathlib_cache=false` (unless a separate cache refresh is explicitly approved). The workflow pins `leanprover/lean4:v4.32.1` and mathlib `520045ab14e26149ee970e2e617ca04b09bde5d6`. This workflow is manual-dispatch on the protected CACE runner; no dispatch or kernel result has been obtained in this continuation. Do not confuse this file with the earlier proposed `SimplexBoundaryDistribution.lean`, which is not present in this CACE branch tree.

Protected signer and orchestrator boundary: the MCP key-initialization tool and capability report are code-only. No key has been generated on OCI, no trust key has been independently provisioned, no feature flag enabled, no live Merlin resolver request made, and no production signer call performed. Existing `merlin-cace-protected-orchestrator.yml` requires manual dispatch on `main` with a successful OCI execution run ID; the PR is still stacked/draft and the workflow has not been dispatched. Thus steps 3–6 remain operationally blocked pending protected configuration, main integration and authorized workflow dispatch.


## 2026-11-14 source-provenance binding requirement and exact-head validation

A source-side gap was found: the original Merlin `resolve_artifact_ref` returned the exact version, bytes metadata and verification state, but did not store or return the source commit/artifact identity. Merely signing a caller-supplied source commit would not independently bind that commit to the stored artifact version.

CACE now fails closed unless `resolution.provenance` is present and exactly matches:
- schema `merlin-artifact-provenance/1`;
- `source_repo` and full 40-character `source_commit`;
- `artifact_id`, `artifact_kind`, `artifact_schema`.

CACE compares this resolver-owned provenance against the caller's requested identity before both attestation and independent verification. The provenance is then bound in the signed statement and exact EvidenceBundle. Missing or substituted provenance is rejected.

Merlin PR #144 now implements the corresponding immutable source-side table and resolver response. The generated preview/directive writers populate it only when deployment identity variables are configured. Existing versions without provenance remain unqualified; no retroactive mutation is allowed. Production still needs `MERLIN_SOURCE_REPO=Mannyspiro/expert-robot` and `MERLIN_SOURCE_COMMIT=<deployed full Git SHA>`.

Latest CACE validation:
- Collaboration validation #43601704421 SUCCESS on exact head `bb69228989e972756510a86ef0040999f66d6f9e`: https://github.com/morganaspim/Cace-app/actions/runs/43601704421
- Lean Source Sanity #43601704583 SUCCESS on the same exact head: https://github.com/morganaspim/Cace-app/actions/runs/43601704583
- Collaboration evidence artifact `14116493756`, SHA-256 `c6af772ddb022861c53a972bb0ef1deab42ad09a778fb912d39db08e2201f6b1`.
- The collaboration run includes the provenance-required CACE round-trip and mutation tests. The source-sanity pass also confirms the F-032 exact-pin runnable/canonical workflow mirror is now byte-identical.

This is still source/test validation only. No live authenticated resolver request, production source identity environment configuration, signer key generation, independent trust provisioning, protected signer call, protected orchestrator run or exact-pin Lean kernel compile has occurred.


## 2026-11-14 exact-head CACE ArtifactRef + continuum validation and cache-lock hardening

CACE code head `24bfc5b920bfb2af6abf2de076f04c2c29bc95fe` passed:
- Collaboration validation #43601889665 — SUCCESS: https://github.com/morganaspim/Cace-app/actions/runs/43601889665
- Lean Source Sanity #43601889638 — SUCCESS: https://github.com/morganaspim/Cace-app/actions/runs/43601889638
- Collaboration evidence artifact `14117195243`, digest `sha256:c9450d12ede4db886d52e4a309f3e0b37ab3a7e75471ec2af92b433b23fc49a5`.

The collaboration suite includes the separate ArtifactRef CACE attestor/verifier, resolver-owned immutable provenance checks, exact historical bytes, CACE Ed25519 sign/verify round-trip and mutation tests, one-time signer key creation/symlink rejection, C++ exact-byte continuum smoke tests, and the independent pure-Python RP²/SNF reference. The run also built the exact-byte CACE continuum EvidenceBundle and confirmed the canonical qualified baseline remains an ancestor.

Defect classes added:
- F-032: runnable exact-pin workflow and canonical template drift; byte-equality guard retained.
- F-033: cache lock inside an atomically replaced package directory; moved to stable `/var/lib/cace-cache/locks/` namespace and structural guard added.

The follow-up head `24bfc5b9` includes both fixes; the two checks above passed on that exact head. PR #102 later advanced with documentation-only commits to `33e8303ae40c5677e23e747cdb86cf72c2807719`; code-validation evidence remains bound to `24bfc5b9`.

Still not production-qualified:
1. Configure and independently review `MERLIN_SOURCE_REPO` and `MERLIN_SOURCE_COMMIT` on the deployed Merlin service, plus the CACE resolver URL/token.
2. Provision the dedicated ArtifactRef signer key and digest-pinned CACE trust material in the protected OCI secret/host boundary.
3. Execute a live historical resolve → CACE attest → independent verify and retain the signed receipt.
4. Run the protected main-only orchestrator validator against the exact successful OCI execution; no such run is recorded.
5. Run the manual exact-pin Lean preflight on `CACEFormal/ContinuumSimplexCore.lean` with `compile_root=false`, Lean `v4.32.1`, Mathlib commit `520045ab14e26149ee970e2e617ca04b09bde5d6`; no kernel compile receipt exists yet.
6. Preserve the independent RP²/SNF result as engineering evidence only until CACE signs the exact source/artifact binding and the formal target is independently qualified.

No production secret, signer key, trust store, environment variable, feature flag, OCI host/IAM state, live resolver request, protected orchestrator run, or deployment was changed by this work. PR #102 remains OPEN/DRAFT and stacked.


## 2026-11-14 live exact-head continuation

Live GitHub state was re-queried after the previous handoff snapshot.

### Paired Merlin source PR #144
- Source repository: `Mannyspiro/expert-robot`.
- Current branch: `feat/merlin-artifact-version-lineage-20261113`.
- Exact current head: `5c61749cb1083e55804e0a3a9df2bad41f901f1b`.
- Native CI #3883, run `43602313717`: **SUCCESS**. Build, focused Hermes/CACE/research groups, C++ tests, independent machine-readable RP² and persistence homology audit, engineering IR/CAD, guardrails, and smoke tests completed.
- Unified platform #518, run `43602313718`: **SUCCESS**. Compile, HUD syntax, unified platform tests, and evidence upload completed.
- Unified evidence artifact `14116637887`, SHA-256 `d359aa6d268aaea2287d4575f138abf856f4f359fd3802c3b4504f921a6b36b9`, bound to the exact head above.
- These are engineering CI results. They do not establish CACE signing, Lean kernel qualification, deployment, or promotion.

### CACE PR #102
- Current branch: `fix/lean-proof-hole-guard-regex-20261113`.
- Current PR head: `f0263f83390a9979b9254cd5b7dcfe0b28df9c5c`.
- The current head is four documentation-only commits beyond code head `24bfc5b920bfb2af6abf2de076f04c2c29bc95fe`; a live compare confirmed only `docs/CROSS_CHAT_HANDOFF.md` and `docs/MERLIN_PRODUCTION_HANDOFF.md` changed in those four commits.
- Exact-current-head Collaboration Validation #712, run `43602061080`: **SUCCESS**. The exact checkout, repository-wide Actions policy, collaboration lifecycle, read-only OCI inventory/protocol probe, collaboration/formal-preflight tests, exact-byte EvidenceBundle build, baseline ancestry check, and artifact upload all passed.
- Retained artifact `14116563014`, SHA-256 `f6855853743a6043defd8c07f89afa4b8075486edc201fc3dfc1435fc589444c`, bound to exact PR head `f0263f83390a9979b9254cd5b7dcfe0b28df9c5c`.
- Lean Source Sanity #308, run `43602060984`, was **CANCELLED before a job started**; no pass is claimed for that workflow on the current docs-only head. The unchanged code head `24bfc5b9` previously passed both Collaboration Validation #686/run `43601889665` and Lean Source Sanity #? / run `43601889638`; those results remain bound to `24bfc5b9`.
- PR #102 remains OPEN/DRAFT and stacked on PR #101. Do not merge independently.

### Remaining six production gates
1. Configure and review deployed Merlin source identity (`MERLIN_SOURCE_REPO`, full `MERLIN_SOURCE_COMMIT`) and CACE authenticated resolver URL/token.
2. Provision the separate ArtifactRef signing key and independently pinned trust material within the protected OCI boundary.
3. Perform live authenticated historical resolution, independent byte/size/digest checks, CACE attestation, and a separate verification; retain the signed receipt.
4. Run the distinct protected main-only orchestrator validator linked to that exact OCI execution.
5. Dispatch the manual exact-pin Lean preflight for `CACEFormal/ContinuumSimplexCore.lean`, `compile_root=false`, Lean `v4.32.1`, Mathlib `520045ab14e26149ee970e2e617ca04b09bde5d6`; no kernel compile receipt exists yet.
6. Preserve RP²/SNF and persistence evidence against exact source bytes; these remain engineering results, not formal qualification.

No production secret, signer key, trust store, service environment variable, feature flag, OCI host/IAM setting, live resolver request, protected orchestrator run, deployment, merge, or promotion was changed or performed in this continuation. Missing production configuration remains an external authorization/provisioning gate, not a reason to weaken fail-closed behavior.
