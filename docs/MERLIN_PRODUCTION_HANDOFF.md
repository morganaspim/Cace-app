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
