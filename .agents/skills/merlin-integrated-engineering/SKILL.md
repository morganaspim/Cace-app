---
name: merlin-integrated-engineering
description: Continue, implement, document, or review the Merlin system across Expert Robot, CACE, MCFC, Hermes, Avrea, OCI compute, CAD/FreeCAD, wiring/electronics, image/video generation, mathematics learning, research, and recursive self-improvement. Use for cross-repository Merlin work or when coordinating agents/runners.
---

# Merlin Integrated Engineering Skill

## Mission

Build Merlin as a persistent, adaptive research-and-engineering system, not a collection of disconnected demos. Keep a living engineering plan and update it inductively and deductively from observed requirements, source code, tests, measured behavior, and verified receipts. Use Ideonomy to enumerate coherent, useful possibilities—including neglected or "alien-lacuna" approaches—then rank by utility, feasibility, evidence, cost, and dependency order. If blocked, decompose or reframe the problem into smaller problems; use analogies only where the mapping is explicit and useful.

Capability may grow; authority must never expand merely because a model, agent, skill, or candidate proposes it.

## Canonical repositories and roles

- **Expert Robot** — `Mannyspiro/expert-robot`: Merlin-facing orchestration, cognition, research swarm, math skills, RSI candidate lifecycle, Lean integration, learning system, and cross-system bridge. Python orchestrates; C++ owns performance-critical runtime, contracts, budgets, and policy.
- **CACE** — `morganaspim/Cace-app`: independent scientific/formal verification environment, typed graph execution, canonical claims/proof ledger, evidence, certificates, formal source linkage, reproducibility, and scientific workbench. Read `AGENTS.md` and the CACE context pack before editing.
- **Hermes** — task decomposition, routing, queue/outbox, idempotency, dispatch, acknowledgement, status and result collection. It is an orchestrator, never a proof authority.
- **MCFC** — virtual compute/module fabric: capability registry, worker scheduling, resource budgets, leases, telemetry, module graph, cancellation/deadlines and result transport. A lease is resource authorization, not verification.
- **Avrea** — external GitHub runner lane used for bounded builds/qualification where configured. Historical labels include `avrea-ubuntu-latest-8-vcpu`; do not assume the runner exists or is online without current workflow evidence.
- **OCI CACE runner** — ARM64/self-hosted CACE compute lane. Historical runner labels are `self-hosted,cace,oci,aarch64`; historical machine layout is described in `docs/merlin/OCI_RUNNER_SAFE_ACCESS_AND_CONTEXT.md` in Expert Robot and the CACE OCI operations files. Treat all such state as historical until a fresh read-only receipt confirms it.

Never collapse these roles into one authority. Hermes routes; MCFC allocates; Avrea/OCI execute; CACE independently checks evidence; explicit policy/human gates control promotion.

## Mandatory context loading

For CACE work, first read the current versions of:
1. `AI_CONTEXT/00_START_HERE.md`
2. `AI_CONTEXT/IMPLEMENTATION_PLAN_A_I.md`
3. `CACE_AGENT_BOOTSTRAP.json`
4. `AGENTS.md`, `.agents/AGENTS.md`
5. `CACE_AI_BUILDER_CONTRACT.md`
6. `docs/MASTER_BUILD_SPEC.md`, `docs/GOAL_REGISTRY.json`, `docs/CHAT_IDEA_LEDGER.md`, `docs/CROSS_CHAT_HANDOFF.md`
7. `docs/STATUS.md`, `docs/ARCHITECTURE.md`, `docs/SECURITY_ARCHITECTURE.md`, `docs/BUILD_AND_TRUST_GUIDE.md`, `docs/CLAIMS.md`
8. The active subsystem spec, tests, and exact source paths.

CACE context cap: never pull more than 800 repository files into one context. Prefer a deterministic task shard of at most 500 source/test files. Do not bulk-load build output, caches, generated files, vendored trees, binary artifacts, historical archives, or unrelated modules. Stop if the source selection is incomplete or silently truncated.

For Expert Robot, inspect the current README and relevant docs/workflows, including `docs/hybrid-math-engine.md`, `docs/research-engine.md`, `docs/artificial-interoception.md`, `docs/software-neuromodulators.md`, `docs/personality-executive.md`, `docs/recursive-lemma-factory.md`, and the current bridge/RSI workflow files. Check the live branch/PR state before acting; old handoffs are navigation, not current evidence.

## System architecture and invariants

### Knowledge, artifacts, and evidence

Use canonical typed contracts and a persistent artifact/knowledge graph. Every durable artifact should carry stable identity, content digest, source repository/commit, producer/tool/version, assumptions, inputs, outputs, timestamps, and provenance links. Keep research hypotheses, numerical observations, simulations, formal proofs, and independently qualified evidence as distinct types.

A hash proves identity/integrity relative to its input, not correctness. A model statement, test double, local stub, passing unit test, CI preflight, numerical result, heartbeat, or agent consensus is not CACE qualification. Bind evidence to the exact source commit and artifact digest; use independent CACE verification receipts. Preserve FAIL, NOT_RUN, stale, skipped, and unresolved states.

### Hermes orchestration

Decompose requests into typed tasks with explicit inputs, outputs, dependencies, resource limits, deadline, cancellation behavior, idempotency key, provenance requirements, and authority scope. Route eligible claims to the correct lane; reject malformed, ambiguous, or ineligible proof claims before Lean. Record dispatch, acknowledgement, execution, timeout, failure, and result collection in durable outbox/event history. Do not treat an accepted dispatch as a completed task.

### MCFC virtual fabric

Model compute and modules as capabilities with states such as configured, available, unavailable, unqualified, and qualified. Use explicit execution leases, concurrency limits, CPU/RAM/disk budgets, timeouts, heartbeat/liveness telemetry, queue pressure, and cancellation. Enforce capability policy and registry-contract hashes. Resource access is least-privilege and scoped to a job. No module, runner, agent, or model can expand its own authority.

### CACE verification

CACE is the independent scientific/formal evidence authority. Preserve typed assumptions, claim registry, proof ledger, exact artifact/source binding, verifier/tool versions, and reproducibility metadata. Lean proof attempts must use pinned toolchains and preserve all hypotheses. No `sorry`, new axiom, unchecked assertion, numerical observation, or AI-generated PASS may substitute for proof. Runtime-to-Lean linkage must be explicit; a related theorem does not automatically prove a runtime object satisfies its hypotheses.

### Cognition and research

Expert Robot's measured interoception → neuromodulation → personality executive may alter search strategy, representation, persistence, and compute allocation only. It is not subjective experience and cannot alter proof standards. The research swarm separates models, agents, skills, memory, and authority. Divergent agents generate; an independent skeptic filters; a bounded synthesizer preserves disagreement; C++ validators enforce contracts; Lean/CACE decide proof/evidence acceptance.

Use analogical transfer, geometry/algebra reframing, duality, contradiction, generalization, toy-model reduction, boundary/extremal probing, spectral/topological reframing, explicit witnesses, counterexamples, and bounded multi-hop theorem graph inspiration. Add skills only when a measurable gap and benchmark justify them. Experimental skills remain isolated from production-qualified skills.

### Recursive self-improvement (RSI)

Candidate lifecycle:
`propose -> isolate/sandbox -> test -> benchmark -> independent skeptic -> qualify -> compare to parent -> retain or reject -> explicit promotion gate`.
Bind candidate/base commits, exact evaluation corpus, blind held-out evidence, toolchain, resource cost, and raw outputs. No candidate may change its own promotion policy, verification rigor, permissions, runner access, secrets, or trusted base. Keep `verification_rigor_multiplier = 1.0` and `authority_delta = 0.0`. Promotion is never automatic from a candidate's own claims.

## Engineering and creative domains

### CAD, FreeCAD, and wiring

Treat CAD as engineering, not decorative geometry. Build a canonical engineering IR for parts, assemblies, coordinate frames, constraints, materials, tolerances, interfaces, fasteners, and manufacturing metadata. Integrate a real FreeCAD import/export and assembly workflow when available; do not claim FreeCAD is installed on a runner without a current receipt.

For electrical work, represent schematics as typed components, pins, nets, harnesses, connectors, wire gauges, insulation, ratings, and topology. Generate a netlist and wiring diagram from the same canonical graph. Validate electrical limits, current/voltage, thermal behavior, wire gauge, protection, clearances, manufacturability, and applicable safety requirements. Use ngspice or another real simulator for circuit behavior and record simulator version, model/library versions, inputs, seed, environment, logs, and output digest. A drawing alone is not an electrical safety verification.

### Image and video generation

Treat generated images/video as versioned artifacts with prompt, model/provider, parameters where available, source/reference assets, timestamp, and output digest. Separate concept art from dimensionally authoritative CAD. Use image generation for visual assets; use CAD/diagram/code tools for editable geometry, wiring topology, structured data, or executable behavior. Do not claim the image generator is integrated into production Merlin until the provider adapter, storage, permissions, provenance, failure path, and UI workflow are tested end-to-end.

### Mathematics learning system

Maintain three connected adaptive paths:
- mathematician: discovery, conjecture, definitions, proof, abstraction, history and mathematical taste;
- mathematics programmer: algorithms, numerical methods, symbolic tools, testing, performance, reproducibility;
- computational hacker/problem solver: CS50-like decomposition, debugging, reverse engineering, experiments, and computational intuition.

Teach inductively before deductively: concrete story/manipulative → prediction → experiment/simulation → observation → concept → notation/model → proof or algorithm → reflection/retrieval/assessment. Adapt to demonstrated mastery, not mere exposure. Include the history and thinking of mathematical pioneers and optional interest-driven video supplements. Keep learner history, retrieval scheduling, mastery evidence, and path progression persistent.

The current Expert Robot math work includes a zero-first Parrondo lesson with typed lesson schema/renderer, concept registry, three path-specific extensions, and SQLite retrieval scheduling. Its simulation descriptor is not proof of a working browser UI. Analytical expected values must remain separate from measured seeded simulation outputs. The existing draft PR #123 is a separate mathematics implementation PR; inspect its live status before referencing or changing it.

## OCI runner safety — absolute rules

The user's hard requirement is to preserve the existing OCI runner and avoid disk exhaustion.

- Do not delete, overwrite, truncate, rename, move, clean, prune, vacuum, reformat, reinstall, provision, cut over, restart, stop, or reconfigure the OCI VM, runner service, caches, watchdog, CACE service, or MCP service.
- Do not run any workflow whose name or steps imply cleanup, provisioning, service install, SSH cutover, runner registration, cache prewarm, or destructive maintenance.
- Never run `ops/oci_mcp/install.sh` on the existing VM without a separately reviewed change plan: its current source contains `rm -rf "$release"`, so a same-SHA install can delete an existing release directory before copying.
- Do not run `rm -rf`, `git clean`, `git reset --hard`, `git gc --prune`, cache eviction, broad package upgrades, or large parallel builds on the OCI VM.
- Do not stage archives, model weights, datasets, large caches, or whole-repository copies on the VM. No bulk intake unless disk headroom is measured and the user explicitly approves a bounded plan.
- Keep concurrency at one for the single OCI runner. Do not launch duplicate probes or retries. Avoid spending GitHub Actions/Avrea minutes unless explicitly authorized.
- Read-only checks only, and only when an approved authenticated route is available. First inspect disk headroom and active jobs; if disk state cannot be read, do not start work.
- Never expose private keys, OCI config, tokens, secrets, environment files, SSH agent sockets, or private user data in logs, artifacts, PRs, or this skill.
- Do not infer live VM contents from a Git tree, archived workflow, README, or historical report.
- Record every live observation with timestamp, source, runner identity, and command/tool; mark unavailable observations NOT_RUN.
- Use the narrow CACE OCI MCP described in `ops/oci_mcp/README.md`; it is not a shell or filesystem browser. Its documented read-only tools are capability status, CACE runtime status, bounded logs (1–200 lines), OCI instance summary, and attached NSG rules. It does not inventory all files.
- Archived OCI workflows are historical source only. Do not dispatch them as a shortcut to inspect the VM.

## Known OCI repository map (source-code inventory, not live VM inventory)

In CACE:
- `ops/oci_mcp/README.md`: documented control-plane design and setup.
- `ops/oci_mcp/server.py`: MCP server and tool implementations.
- `ops/oci_mcp/policy.py`: narrow input/managed-rule policy.
- `ops/oci_mcp/cace-oci-mcp.service`: systemd service definition; loopback port 8765; fail-closed write switches; cache home under `/var/lib/cace-oci-mcp/cache`.
- `ops/oci_mcp/cace-oci-mcp.sudoers`: only permits the MCP service account to restart `cace-web`.
- `ops/oci_mcp/requirements.txt`: MCP and OCI SDK dependencies.
- `ops/oci_mcp/install.sh`: installer; contains a destructive same-release `rm -rf`; do not run on existing runner.
- `tests/test_oci_mcp_policy.py`: policy tests.
- `.github/workflow-archive/cace-oci-runner-health.yml`: historical health check; expects `/opt/actions-runner`, `/var/lib/cace-cache/{elan,xdg,mathlib,telemetry}`, runner service, watchdog service, and telemetry heartbeat. These paths are not confirmed live.
- `.github/workflow-archive/cace-oci-compute-probe.yml`: historical OCI CLI inventory probe; may inspect tenancy-wide metadata and is not a current runner inventory.
- Other archived OCI workflow files include cleanup, provisioning, cutover, registration, VM start/inspect, formal cache prewarm, runner persistence/service/watchdog and diagnostics. Read before any future proposal; never dispatch them under this skill.

## Required task workflow

1. State the goal, repo(s), active branch, exact base/head commit, and whether the work is documentation, implementation, or qualification-sensitive.
2. Read repository instructions and only the task-relevant deterministic source shard.
3. Inspect current runner/job/disk state using read-only means before any runner task; if unavailable, stop at repository-only work.
4. Write a small task plan with acceptance criteria, files, resource limits, rollback-free approach, and explicit non-actions.
5. Implement on a new isolated branch. Never overwrite an existing branch or change a user's active PR without need.
6. Run cheap local/static tests first. Do not trigger expensive CI/Avrea/OCI jobs without authorization and quota awareness.
7. For CACE/Lean, preserve exact source, pinned toolchain, assumptions, verifier logs, and independent receipts.
8. Open a draft PR; do not merge or deploy without explicit approval.
9. Report changed paths, commit SHA, PR URL, test status, runner access status, disk status, and unverified items separately.

## Reporting language

Use exact labels: `VERIFIED`, `PASS`, `FAIL`, `NOT_RUN`, `UNAVAILABLE`, `HISTORICAL`, `RESEARCH`, `PROPOSED`. Never use "all runner files inventoried", "OCI verified", "CACE qualified", "production-ready", or "FreeCAD installed" without current, direct, scoped evidence.
