# CACE Local Agent Runtime / Typed Tool Bus v1

Status: implementation/security architecture for A-I Track F / Goal G066. Not scientific, proof, qualification, or production evidence.

## Purpose

This slice gives CACE a concrete provider-independent local agent execution boundary without placing an LLM inside the trusted verification base.

The model is an **untrusted planner**. It cannot directly call Python, C++, Lean, a shell, the network, a package manager, the filesystem, claim promotion, or proof-ledger APIs. Its only executable path is:

`planner -> typed AgentDecision -> ToolBus -> capability policy -> strict request decoder -> canonical CACE handler -> typed result -> bounded observation`

A successful Tool Bus result remains orchestration/observation only:

- `proof_effect = "none"`
- `promotion_authority = false`

Canonical verification continues to come from the existing CACE module/verifier/formal-gate/proof-ledger architecture.

## v1 components

### `cace_studio/agent_runtime/contracts.py`

Defines:

- explicit `Capability` values;
- fail-closed `CapabilityPolicy.zero_contact()`;
- strict dataclass request/response contracts;
- canonical model-facing tool descriptors;
- tool call/result envelopes;
- hashed audit records.

### `cace_studio/agent_runtime/tool_bus.py`

Provides:

- duplicate-safe typed tool registration;
- denied-tool hiding from planner discovery;
- human-approval hooks for consequential capabilities;
- strict request decoding with unknown-field rejection;
- canonical input/output SHA-256 identities;
- fail-closed response type checking;
- append-only in-memory action audit for the runtime session.

### `cace_studio/agent_runtime/controller.py`

Provides:

- bounded step/tool/failure budgets;
- planner/action/observation loop;
- strict JSON-only `LocalJSONPlanner`;
- size-bounded observations;
- fail-closed model parsing;
- no execution of free-form model text.

The existing `AIProvider` abstraction remains the provider boundary. Current concrete local providers are already loopback-only and refuse redirects/environment proxies.

### `cace_studio/agent_runtime/core_tools.py`

Initial canonical tools are intentionally narrow:

- `cace.runtime.native_status`
- `cace.registry.list_modules`
- `cace.experiment.describe_active`
- `cace.experiment.run_active`

`run_active` delegates to the existing `GraphExecutor`; it does not duplicate scientific execution or proof semantics inside the agent layer.

The execution tool may run the existing active graph (or selected-upstream closure) and may supply ordinary external node inputs. It cannot edit the graph or promote evidence.

## Zero-contact capability policy

Allowed in v1:

- read module/catalog metadata;
- inspect runtime status;
- inspect active experiment identity;
- run existing scientific/checker operations exposed as typed tools.

Human approval required:

- canvas mutation;
- workspace writes;
- tool proposals/incubation handoff.

Hard denied:

- general network;
- direct shell;
- package installation;
- self-modification;
- proof-source writing;
- claim/proof promotion;
- secret access;
- wallet-key access.

A hard-denied capability stays denied even if a tool with that capability is accidentally registered.

## Security/rigor invariants

1. AI output is never evidence.
2. Denied tools are omitted from the planner-visible registry.
3. Every known tool call is capability checked before its handler executes.
4. Request payloads must be canonical JSON-compatible data before execution.
5. Request contracts reject unknown fields.
6. Handler return values must match the declared response dataclass.
7. Tool input/output hashes establish identity/provenance only; they do not establish correctness.
8. The Local Agent cannot directly mutate canonical proof/claim state.
9. Graph execution remains owned by `GraphExecutor`.
10. The application remains usable with AI disabled.

## Deliberate v1 limits

This is the first runtime slice, not completion of G066/G010.

Still required before high-autonomy production use:

- OS/process sandbox enforcement and CPU/RAM/process/disk/time quotas;
- durable action-log persistence independent of the model;
- heartbeat + lease + checkpoint/recovery wiring;
- typed canvas mutation tools with preview/diff/approval;
- typed Research Idea and Tool Request tools;
- capability-broker process separation for Hybrid/General Agent modes;
- tool-result artifact store and bounded data inspection;
- adversarial/fuzz testing of the bus boundary;
- GUI controls for approvals, budgets, agent mode, pause/cancel and audit review.

## Acceptance tests in this slice

`tests/test_agent_tool_bus.py` checks that:

- valid requests execute through declared types;
- unknown request fields fail closed;
- network capability is denied without handler execution;
- approval-required mutation fails closed without approval;
- wrong handler response types fail closed;
- controller tool loops obey budgets;
- registry/experiment tools expose canonical CACE state without proof authority;
- active experiment execution delegates to the canonical executor;
- the local planner accepts only strict JSON and only planner-visible tools.

No Lean/canonical proof qualification is required merely because this non-proof runtime layer exists. If a later tool binds runtime objects to formal hypotheses or changes qualification-sensitive paths, that change must follow the normal source-to-formal and exact-current-head qualification gates.


## v1.1 durable audit and recovery

The runtime now has an optional recovery layer that remains outside scientific/proof authority.

### Hash-chained local audit journal

`HashChainedAuditJournal` persists Tool Bus audit records as append-only JSONL with:

- per-entry SHA-256 identity;
- a previous-entry hash link;
- explicit session identity;
- fsync before returning from append;
- verification on reopen;
- tamper detection for ordering or content changes.

The journal is engineering/provenance evidence only. Its hash chain cannot create verification PASS, FORMAL status, or proof-ledger promotion.

### Atomic checkpoints

`FileCheckpointStore` stores a content-hashed `AgentCheckpoint` in a trusted host-configured directory. Writes use same-directory exclusive temp files, fsync, and atomic replacement.

Checkpoint state includes:

- run/task identity;
- next planner step;
- consumed tool/failure budgets;
- monotonic heartbeat sequence;
- bounded observations;
- typed trace serialization;
- an optional pending tool call;
- terminal/running state.

The model never selects the checkpoint path.

### Fail-closed replay rule

Before invoking a tool, the controller durably checkpoints that call as pending. The pending marker is cleared only after the call result has been handled and the post-call checkpoint is written.

If a restarted controller finds a pending call, it returns `recovery_blocked` and does **not** replay the call automatically. This is intentionally conservative because the prior process may have executed the operation before stopping.

The same rule is used when a configured durable audit journal fails after a tool returns: continuation stops with the pending call preserved for inspection.

### Process-local leases

`AgentLeaseManager` prevents two controllers in the same local runtime from owning one run simultaneously. It uses monotonic time and expiring generations.

Leases are deliberately process-local in v1.1. Restart clears stale ownership; the durable checkpoint remains the recovery authority. Cross-process/distributed leases remain later work.

The controller renews its lease immediately before committing a pending tool action, so planner/model latency cannot carry an already-expired lease into execution. v1.1 does **not** claim distributed exactly-once behavior for a tool call that itself runs longer than the lease TTL. Until mutation-specific transactions/idempotency and stronger worker coordination exist, the configured TTL must exceed the expected maximum duration of an individual tool call.

### Agent liveness heartbeat

The controller can emit `AgentHeartbeat` records with monotonic sequence, phase, step, resource-budget counters, lease identity, and checkpoint digest.

Agent heartbeat is coordination metadata only:

- `evidence_authority = false`
- `proof_effect = "none"`
- `promotion_authority = false`

This is intentionally separate from the canvas/scientific heartbeat. Later integration may feed canvas deltas into planner context, but liveness/checkpoint state cannot create canonical verification state.

### Remaining recovery hardening

v1.1 still does not claim distributed exactly-once execution. Before approved mutation tools become high-autonomy production capabilities, CACE still needs:

- mutation-specific transactional/idempotency contracts;
- OS/process sandbox quotas;
- independent durable storage/mirroring policy for audit/checkpoint bundles;
- cross-process lease/worker coordination if multiple workers are enabled;
- GUI recovery inspection and explicit retry/resolve actions;
- crash/fault injection around every pre-call/post-call durability boundary;
- retention/redaction policy for tool observations.


## v1.2 canonical experiment perception

The Local Agent can now receive a live, bounded `cace-agent-perception-v1` packet through an optional controller perception provider. This implements the existing contract in `schema/cace-agent-perception.schema.json`; it does not create a competing scientific heartbeat or evidence system.

### Canonical evidence derivation

`AgentPerceptionTracker` accepts an `Experiment` and, optionally, a real `RunResult`.

Per-node canonical evidence state is derived only from real CACE `VerificationRecord` objects:

- any canonical FAIL record -> `FAIL`;
- non-empty all-PASS records -> `PASS`;
- absent/mixed NOT_RUN records -> `NOT_RUN`;
- a run whose recorded source semantic graph hash differs from the active experiment -> `STALE`.

Fabricated mapping/dictionary objects presented as verification records are rejected.

Heartbeat display state can mirror those canonical observations (`VERIFIED`, `FAILED`, `STALE`) or show non-evidentiary runtime attention states such as `ACTIVE`, `VERIFYING`, `BLOCKED`, and `DORMANT`. It never writes verification state.

### Semantic change and compact sensory context

Each node receives a content hash over its canonical node identity, module ID, parameters, and incident semantic edges. Layout/presentation coordinates are excluded.

Successive packets expose:

- a monotonic perception sequence;
- semantic-change flags;
- optional residual norm and improving/stable/worsening trend;
- optional convergence progress;
- bounded resource pressure;
- bounded research-interest metadata;
- upstream blocker references;
- the active experiment semantic graph hash;
- the originating run ID when one exists.

Residual trends and research-interest values are coordination/navigation signals only. They are not verification evidence.

### Controller boundary

When a perception provider is configured, `AgentController` validates the packet's top-level v1 contract and requires `evidence_authority=false` before including it in `AgentTurnContext`.

A configured perception provider that fails or returns a malformed/authoritative packet aborts the run. The planner is not silently given stale substitute context.

Perception is read-only. v1.2 grants no new Tool Bus capability and no canvas-mutation authority.


## v1.1.1 exact pending-result recovery

The durable audit journal now has a backward-compatible schema v2. New controller writes persist both:

- the canonical `ToolAuditRecord`; and
- the matching typed `ToolResult`.

This closes the safe crash window between **tool completed + audit fsync** and the later post-call checkpoint. On resume, if the checkpoint still says a call is pending but the v2 journal contains a hash-verified matching result, the controller restores that result into the trace/observation stream and continues **without invoking the tool again**.

Recovery remains fail-closed when:

- no typed durable result exists for the pending call;
- the audit chain fails verification;
- the durable record's tool name or input hash differs from the pending call;
- the checkpoint's original budget differs from the resumed controller budget; or
- the Tool Bus descriptor fingerprint changed since the checkpoint.

New checkpoints therefore bind:

- `max_steps`;
- `max_tool_calls`;
- `max_failures`;
- `max_observation_chars`; and
- a canonical SHA-256 fingerprint of the planner-visible typed Tool Bus contract.

Older v1.1 checkpoints remain readable for compatibility, but only checkpoints created after this hardening carry those additional resume constraints.

This still does not claim general distributed exactly-once mutation semantics. If a process stops after a tool side effect but before a v2 result is durably journaled, CACE retains the pending marker and blocks automatic replay.


## v1.3 durable cross-process lease + operation idempotency

This slice closes the remaining local multi-process coordination gap before CACE exposes approved canvas-mutation tools to an autonomous planner.

### Filesystem-backed fencing lease

When an `AgentController` is configured with a `FileCheckpointStore`, it now defaults to a `FileAgentLeaseManager` rooted under the trusted checkpoint directory.

The durable lease manager:

- serializes lease transitions with an OS advisory file lock;
- stores a content-hashed lease record;
- retains the previous generation after release or expiry;
- increments the generation on every acquisition;
- rejects stale renewals whose lease ID, owner, or generation no longer matches;
- uses wall-clock expiry because the record must be meaningful across processes;
- remains coordination metadata only with no proof/evidence authority.

The lease generation is a fencing epoch. It is attached to each controller-generated Tool Bus call so future mutation handlers can reject stale owners at their own transactional boundary.

### Deterministic operation / transaction IDs

Every controller tool action now gets a deterministic `operation_id` derived from:

- run ID;
- tool-call ordinal;
- canonical tool name; and
- canonical arguments.

The planner never chooses the operation ID, lease ID, or fencing generation.

The resulting `ToolCall` carries:

- `operation_id`;
- `lease_id`; and
- `lease_generation`.

Those fields are propagated into `ToolContext` for canonical handlers that need transaction-aware writes.

### Durable operation ledger

`FileOperationStore` provides a per-operation cross-process ledger with content-hashed atomic records and OS-locked claim/commit transitions.

States are intentionally small:

- `in_progress`: the operation was durably claimed but there is no committed result;
- `committed`: the exact typed result is durably stored.

Behavior:

1. First claim for an operation/tool/input tuple receives `execute`.
2. A second process seeing `in_progress` receives `recovery_blocked`; the handler is not re-executed.
3. A second process seeing `committed` receives the stored typed result without re-running the handler.
4. Reusing one operation ID for different canonical input/tool identity is rejected as an idempotency conflict.
5. If the handler starts and then errors, returns an invalid response, or its durable operation commit fails, the operation remains unresolved and automatic replay is blocked.

This gives CACE at-most-once automatic execution for one operation ID and replay of committed results. It intentionally does not pretend an uncommitted side effect is safe to repeat.

### Consequential capability gate

The Tool Bus now marks these capabilities as idempotency-required:

- `canvas_mutate`;
- `workspace_write`; and
- `tool_propose`.

Even if human approval is granted, those capabilities fail closed unless both conditions hold:

- the Tool Bus call has a host-generated `operation_id`; and
- a durable `FileOperationStore` is configured.

This gate is in place **before** approved canvas-mutation tools are added.

### Dual-source recovery

A pending checkpoint can now recover a completed call from either:

1. the committed operation ledger; or
2. the typed hash-chained audit journal.

The operation ledger is checked first because it is the idempotency authority. The audit journal remains provenance/history.

An audit result whose status is itself `recovery_blocked` is not treated as a completed safe result.

Neither source creates scientific evidence, verification PASS, FORMAL status, or proof-ledger promotion.

### Remaining boundary before high-autonomy mutation

The remaining work is now narrower:

- transaction-aware canvas mutation commands with preview/diff/approval;
- mutation handlers that verify lease fencing generation at commit time;
- explicit operator resolution for unresolved `in_progress` operations;
- crash/fault injection around claim -> handler -> operation commit -> audit -> checkpoint boundaries;
- storage retention/redaction/mirroring policy;
- OS/process CPU/RAM/disk/time sandbox quotas;
- GUI controls for pause/cancel, lease ownership, pending transactions, approvals, and recovery resolution.



## v1.4 typed canvas mutation: preview -> approval -> fenced commit -> hash verification

Canvas mutation is now an explicit two-tool protocol. The planner never receives direct mutable access to an `Experiment`.

### Typed operations

`CanvasMutationOperation` currently supports a bounded batch of:

- `add_node`;
- `remove_node`;
- `replace_params`;
- `move_node`;
- `add_edge`; and
- `remove_edge`.

The preview path validates the final candidate graph against canonical CACE registry/executor rules, including:

- registered module identity;
- known parameter names;
- existing source/target nodes;
- source/output and target/input port existence;
- exact port type/unit compatibility;
- single occupancy of target inputs; and
- cycle rejection.

Node removal deterministically removes incident edges and removes the node from organizational groups; empty groups produced by that removal are dropped.

### Read-only durable preview

`cace.canvas.preview_mutation` is a `read_experiment` tool. It:

1. deep-copies the active experiment;
2. applies the typed operation batch to the copy only;
3. validates the candidate graph;
4. computes canonical base/target semantic and full experiment hashes;
5. computes the existing canonical `drift_report`;
6. hashes the normalized mutation batch and deterministic diff;
7. derives a content-addressed `preview_id`; and
8. persists an immutable content-hashed preview record.

The active experiment is unchanged during preview.

The preview store re-computes the mutation hash, diff hash, preview identity, and base/target fields when loading a record. A merely self-consistent outer JSON hash is not accepted as sufficient preview identity.

### Approval of the exact diff

`cace.canvas.commit_preview` accepts **only** a `preview_id`.

The model cannot supply a replacement mutation batch during commit.

`canvas_preview_approval_callback(...)` resolves that ID from the trusted preview store and presents the human decision callback with the exact stored:

- operation list;
- structural drift report;
- base semantic/full hashes;
- target semantic/full hashes;
- mutation hash; and
- diff hash.

A denied approval leaves the active experiment unchanged.

### Current fencing, not merely a positive token

Consequential Tool Bus capabilities now require a configured current-lease validator in addition to:

- run ID;
- lease ID;
- positive lease generation;
- operation ID; and
- durable operation store.

Checkpointed `AgentController` instances wire their `FileAgentLeaseManager` into the Tool Bus validator automatically.

Immediately before a consequential handler may execute, the Tool Bus verifies that the supplied lease ID/generation is the **currently active durable fencing token for that run**. A stale process therefore cannot commit a preview after another process has acquired a newer generation.

### Idempotent commit and safe rejection

The commit call continues to use the v1.3 durable operation ledger.

Safe precondition failures such as:

- unknown preview;
- stale base experiment;
- preview-content identity mismatch; or
- deterministic target mismatch before mutation

use `ToolPreconditionError`. These are durably committed as deterministic `invalid_request` results so retries replay the rejection rather than becoming ambiguous in-progress transactions.

Errors that may occur after a generic handler could have begun side effects remain `recovery_blocked`.

### Commit algorithm

After approval, fencing, and idempotency checks, canvas commit:

1. loads and re-validates the immutable preview;
2. verifies the active experiment still matches both approved base hashes;
3. re-applies the stored operations to a fresh copy;
4. re-computes target semantic/full hashes and the deterministic diff hash;
5. refuses commit unless all recomputed values equal the approved preview;
6. replaces the active experiment state with the validated candidate;
7. re-computes the active experiment semantic/full hashes; and
8. requires exact equality with the approved target hashes.

If the final hash verification fails, the in-memory experiment is restored from the pre-commit snapshot and the commit fails closed.

The resulting Tool Bus operation remains:

- `proof_effect = "none"`;
- `promotion_authority = false`; and
- incapable of manufacturing verifier, formal, or proof-ledger state.

### Deliberate boundary

v1.4 mutates the active in-memory `Experiment` owned by the CACE process. It does not yet claim an atomic distributed workspace/database commit shared across independent application processes.

The next hardening layer for production multi-worker mutation is a workspace persistence transaction that atomically binds:

`preview target hash -> lease generation -> operation ID -> persisted experiment version`.

That can reuse the same typed preview, approval, fencing, and idempotency contracts rather than changing planner semantics.


## v1.5 atomic persisted workspace mutation/versioning

v1.5 extends the v1.4 preview/approval/fencing contract across application restarts and multiple CACE worker processes.

### Canonical persisted workspace envelope

`FileExperimentWorkspace` stores one workspace as one atomically replaced, content-hashed JSON envelope.

The envelope binds:

- canonical `.cace` experiment container data;
- `workspace_id`;
- monotonically increasing `version`;
- exact `parent_version`;
- `operation_id`;
- approved `preview_id`;
- `lease_id`;
- lease fencing generation;
- base semantic/full hashes; and
- target semantic/full hashes.

The experiment bytes and transaction metadata therefore cannot be committed as independently drifting files.

The existing `core.serialization` implementation remains canonical. v1.5 factors its data-model conversion into `experiment_to_data(...)` and `experiment_from_data(...)`; the normal `save_experiment` / `load_experiment` functions use the same helpers.

### Workspace version 0

Initialization writes version `0` with:

- no mutation operation;
- no preview;
- no lease identity;
- base hash equal to target hash; and
- the supplied experiment as the persisted source of truth.

If a runtime starts against an existing workspace, the persisted experiment is loaded into the process's active `Experiment` rather than allowing a stale local copy to overwrite the workspace.

### Preview binds N -> N+1

When a canvas runtime has a workspace store, preview is created from the **persisted workspace state**, not merely the process-local object.

The immutable preview additionally binds:

- `workspace_id`;
- `base_workspace_version = N`; and
- `target_workspace_version = N + 1`.

Those values are part of:

- the deterministic diff;
- the diff hash;
- the content-addressed preview identity; and
- the exact human approval payload.

A preview created against workspace version `N` cannot later be committed against version `N+1`.

### Transaction-bound fencing at atomic replace

The generic Tool Bus still validates the current run/lease/generation before an approval-required consequential handler starts.

The persisted workspace commit then performs a **second current-lease assertion while holding the workspace lock immediately before the atomic replace**.

This closes the race where lease ownership could change between Tool Bus entry and durable workspace commit.

### Atomic workspace commit

A persisted canvas commit:

1. loads and validates the approved immutable preview;
2. loads the current persisted workspace;
3. checks exact base workspace version and base semantic/full hashes;
4. recomputes the candidate graph and deterministic diff;
5. checks approved target semantic/full/diff hashes;
6. obtains the workspace lock;
7. re-checks workspace version/base hashes;
8. re-checks the current durable lease fencing token;
9. writes one new content-hashed workspace envelope with version `N+1`;
10. atomically replaces the prior workspace state;
11. re-loads the workspace file; and
12. verifies operation identity, version, semantic hash, and full hash.

Only after that durable verification does the process synchronize its active in-memory `Experiment` to the persisted workspace version.

### Cross-worker optimistic concurrency

Two workers may create previews against the same version `N`, but only the first valid commit can create `N+1`.

Any later commit of a preview still bound to `N` is a deterministic safe precondition failure and does not mutate the workspace.

### Crash reconciliation across the workspace / operation-ledger boundary

The workspace envelope and operation ledger are intentionally separate durable systems. A crash may therefore happen after:

`workspace N+1 committed`

but before:

`operation ledger -> committed`.

To avoid replaying the mutation, `TypedTool` now supports an optional tool-specific `recovery_handler`.

For `cace.canvas.commit_preview` the recovery handler is read-only with respect to durable mutation. When the Tool Bus encounters an existing `in_progress` transaction, it:

1. keeps the handler from executing again;
2. asks the canvas recovery handler whether the atomic workspace record already binds the same operation ID, preview ID, and target hashes;
3. if no exact durable match exists, returns `recovery_blocked`;
4. if an exact match exists, reconstructs the typed commit result from the persisted workspace;
5. commits that result to the operation ledger; and
6. returns the recovered result without applying the canvas mutation again.

This closes the key crash window without claiming a distributed two-phase commit protocol.

### Proof boundary

Workspace versions, transaction IDs, hashes, approvals, and fencing generations remain engineering provenance/coordination state.

They do not create:

- verifier PASS;
- FORMAL evidence;
- theorem qualification;
- proof-ledger promotion; or
- mathematical correctness.

Exact content identity is required for safe mutation, but remains distinct from proof.


### Durable transaction receipt lineage

The persisted workspace envelope also carries a compact immutable receipt for every committed workspace version.

Each receipt binds:

- workspace version and exact parent version;
- commit timestamp;
- operation ID;
- preview ID;
- lease ID and fencing generation;
- base semantic/full hashes; and
- target semantic/full hashes.

The receipt sequence must be contiguous from version 1 through the current version, operation IDs must be unique, adjacent target/base hashes must form a valid chain, and the final receipt must exactly match the top-level current transaction metadata.

Receipts do **not** duplicate old experiment snapshots. They retain only the transaction/version/hash identities required for durable reconciliation.

This closes a deeper crash case:

1. operation A durably commits workspace version 1;
2. A's operation-ledger result is lost before finalization;
3. operation B later commits workspace version 2;
4. A is retried under a newer valid lease generation;
5. the Tool Bus finds A still `in_progress`;
6. the canvas recovery handler locates A's immutable version-1 receipt;
7. A's typed result is reconstructed and its operation ledger is finalized;
8. the active workspace stays at version 2.

Recovery therefore never rolls the workspace backward merely to resolve an older idempotency record.


## v1.6 approved autonomous multi-step canvas plans

v1.6 adds a higher-level plan object above the v1.4/v1.5 mutation transaction layer. The planner may propose a multi-step graph construction plan, but it still never receives direct mutable access to the workspace.

### Plan preview

`cace.canvas.preview_plan` is read-only. A request contains up to 50 typed steps. Every step has:

- a canonical `step_id`;
- zero or more explicit `depends_on` step IDs; and
- one or more existing typed canvas mutation operations.

CACE validates the dependency graph, rejects unknown dependencies/cycles, and deterministically topologically sorts ready steps by step ID.

The plan preview then simulates each step sequentially against a copy of the persisted workspace. Every simulated step creates and persists an ordinary immutable `CanvasPreviewRecord` with the exact future workspace transition:

`N -> N+1 -> N+2 -> ...`

No workspace mutation occurs during plan preview.

### One immutable plan identity

The durable `CanvasPlanRecord` binds:

- workspace ID;
- base and final workspace versions;
- base and final semantic/full hashes;
- deterministic ordered step IDs;
- explicit step dependencies;
- each step's immutable preview ID;
- each step's base/target versions and hashes;
- each step diff hash; and
- dependency estimates.

The content-addressed `plan_id` is the SHA-256 identity of that entire non-proof-authoritative plan object.

`cace.canvas.execute_plan` accepts only the stored `plan_id`. The model cannot insert, remove, reorder, or rewrite plan operations after approval.

### Advisory execution/proof dependency estimate

Plan preview also reports:

- canonical final graph execution node order;
- corresponding module execution order;
- unique module IDs;
- required external inputs not supplied by graph edges; and
- per-module maturity, declared evidence metadata, formal-artifact metadata, and limitations.

This information is advisory planning metadata only. Declared proof metadata is explicitly labeled as **not executed verification evidence** and has no promotion authority.

### One human approval for the entire exact plan

`canvas_plan_approval_callback(...)` resolves the requested `plan_id` from the durable plan store and presents the exact stored plan to the human decision callback.

The approval payload therefore includes the full deterministic ordered plan, every child preview/hash/version transition, final target hashes, and dependency estimate.

The approval applies only to that exact plan identity.

### Durable approval reuse on crash recovery

The operation ledger now persists whether an exact Tool Bus operation was human-approved.

For approval-required idempotent tools, recovery/replay may reuse that prior approval only when all of these still match:

- operation ID;
- canonical tool name; and
- canonical input SHA-256.

Old operation records that do not contain the approval flag default to unapproved and therefore require the normal approval path.

This means an approved plan is not re-prompted merely because the process crashed after durable transaction claim. Changing the plan ID or any tool arguments does not inherit the old approval.

### Step execution is still transaction-based

The plan handler does not perform one giant workspace overwrite.

For every ordered step it derives a deterministic child operation ID from:

- plan ID;
- outer plan operation ID;
- step ID;
- step index; and
- step preview ID.

Each step is then committed through the existing `CanvasMutationRuntime.commit` path with:

- the exact stored child preview;
- the current run/lease/fencing generation;
- the second fencing check inside the workspace lock;
- optimistic workspace version/base-hash checks;
- atomic persisted workspace replacement;
- post-commit hash verification; and
- an immutable workspace transaction receipt.

The plan stops on the first failure.

### Crash/resume

On retry/recovery, CACE examines the workspace receipt lineage before each step.

- A step whose exact child receipt already exists is not executed again.
- The next missing step may execute only if the current workspace exactly matches that step's approved base version/hashes.
- An unexpected workspace state fails closed.
- If some earlier plan steps already committed and a later step becomes unresolved, the outer plan transaction remains recovery-blocked rather than pretending the entire plan failed atomically.

This permits:

`step 1 -> step 2 -> crash -> recover -> step 3 -> ...`

without replaying steps 1 or 2.

### Historical completed-plan reconciliation

If every plan step committed but the outer plan operation ledger crashed before finalization, later workspace transactions may legitimately advance the workspace further.

Recovery uses the immutable child receipt chain to reconstruct the completed plan's historical final result. It finalizes the old outer plan transaction without rolling the current newer workspace backward.

### Final verification

For a normally completing plan, CACE requires the final persisted workspace version and semantic/full hashes to equal the approved plan target exactly.

A recovered historical plan returns the exact approved historical target from its validated receipt chain while leaving a newer current workspace untouched.

### Trust boundary

Plan approval, dependency estimates, child transactions, workspace hashes, and plan completion remain engineering coordination/provenance.

They do not create verifier PASS, FORMAL evidence, theorem qualification, or proof-ledger promotion.


## v1.7 bounded Plan -> Execute -> Observe -> Replan autonomy

v1.7 adds a durable autonomy-session layer above the approved multi-step plan runtime.

The design deliberately does **not** mean “approve once and mutate forever.” One autonomy cycle is the largest approval unit.

A cycle is:

`approved pending plan -> execute exact plan -> run one bounded scientific experiment -> build canonical perception -> optionally preview one follow-up plan`

If a follow-up plan is created, the session returns to `WAITING_PLAN_APPROVAL`. That new plan cannot mutate the workspace until a new approval is granted for that exact plan identity.

### Host-created autonomy session

Autonomy sessions are created by the trusted host/UI through `AutonomyLoopRuntime.create_session(...)`, not by arbitrary planner text.

A durable session binds:

- session ID;
- research objective;
- workspace ID;
- exact pending plan ID;
- immutable run specification;
- explicit autonomy budget;
- cycle/science/replan counters;
- latest canonical perception packet; and
- immutable completed-cycle receipts.

The session store uses cross-process locking, content-hashed envelopes, and atomic replacement.

### Explicit budgets

`AutonomyLoopBudget` bounds:

- total approved cycles;
- total scientific runs;
- total automatic replans; and
- maximum plan steps per cycle.

Budgets are persisted in the session and counters may never exceed them.

When there is no remaining cycle/run/replan budget, the session finishes instead of silently extending autonomy.

### One approval per workspace-changing cycle

`cace.autonomy.advance` accepts:

- `session_id`; and
- the session's exact current `plan_id`.

Its approval callback resolves the durable session and durable plan and presents the human with:

- objective;
- total budget and budget already used;
- exact scientific run specification;
- exact immutable pending plan;
- every child preview/hash/version transition;
- dependency estimates; and
- the explicit post-plan behavior: one science run, perception, and at most one follow-up plan preview.

The plan ID is part of the Tool Bus canonical input hash and operation identity. A new replan therefore cannot inherit approval from a previous plan.

### Science execution

After the approved plan commits, CACE loads the persisted workspace and requires its version and semantic/full hashes to equal the approved plan target.

Only then does the loop execute the canonical `GraphExecutor`.

The run specification can bind:

- selected-upstream target node IDs;
- external inputs; and
- deterministic seed.

An interrupted/incomplete run does not advance the autonomy session.

### Observation

A real `RunResult` is summarized into a non-authoritative `AutonomyRunSummary`.

The same real result is passed to `AgentPerceptionTracker` so canonical evidence states continue to derive only from actual `VerificationRecord` objects.

The perception packet remains:

- `evidence_authority = false`;
- incapable of manufacturing PASS/FORMAL state; and
- observation input for replanning only.

Perception trackers are isolated per autonomy session.

### Strict local-AI replanning

`LocalJSONReplanProvider` adapts the existing loopback-only `AIProvider` interface.

The local model is allowed to return exactly one JSON object:

- `{"action":"finish"}`; or
- `{"action":"replan","steps":[...]}`.

No free-form response is executable.

A replan is decoded into the typed `CanvasPlanPreviewRequest` contract, then processed by the existing deterministic/canonical plan-preview path.

The model cannot:

- execute the follow-up plan;
- grant its own approval;
- mutate the workspace directly;
- create verification evidence;
- promote proof state; or
- bypass plan/graph validation.

### Follow-up plans are preview-only

The replan provider may create at most one follow-up plan per completed cycle.

That plan preview is durable and content-addressed, but it does **not** mutate the workspace.

The autonomy session stores its ID as the new `pending_plan_id` and returns to `WAITING_PLAN_APPROVAL`.

The next mutation requires a distinct Tool Bus operation and a new human approval.

### Durable cycle receipts

Every fully completed autonomy cycle stores an immutable receipt before the outer Tool Bus operation is finalized.

A cycle receipt binds:

- outer operation ID;
- executed plan ID;
- cycle index; and
- the exact typed cycle response, including science run ID, perception, next plan ID, workspace version, and remaining budgets.

If the process crashes after session persistence but before operation-ledger finalization, recovery returns the stored cycle response without:

- re-executing the workspace plan;
- rerunning science;
- invoking the replan model again; or
- asking the human to approve the same exact operation again.

The v1.6 durable approval bit is reused only when operation ID, tool name, and canonical input hash still match exactly.

### Fail-closed post-mutation behavior

Before an approved plan begins, malformed/stale session or plan inputs are safe precondition failures.

After the plan has committed, failures in:

- workspace-target verification;
- scientific execution;
- perception construction;
- local replan generation/validation; or
- durable cycle-receipt persistence

are not misclassified as harmless input errors. They stop automatic continuation and remain recovery-visible.

### Deliberate race boundary

A science observation is only started after the persisted workspace is verified to still equal the just-approved plan target.

If another worker advances the workspace before that check, CACE refuses to observe/replan from the wrong graph.

If a crash occurs after plan completion but before a durable cycle receipt and a later worker advances the workspace, recovery fails closed rather than pretending the later workspace is the approved experiment that was meant to be observed.

### Trust boundary

Autonomy sessions, budgets, plan approvals, run summaries, perceptions, and replans remain orchestration/provenance.

They do not create:

- verifier PASS;
- FORMAL evidence;
- theorem qualification;
- proof-ledger promotion; or
- mathematical correctness.
