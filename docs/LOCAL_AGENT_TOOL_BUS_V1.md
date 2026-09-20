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
