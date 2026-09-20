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

