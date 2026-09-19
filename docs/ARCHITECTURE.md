# CACE Studio Architecture

Status: development architecture for the v3.31+ line. This document describes boundaries and intended contracts; it is not evidence that every planned component is production-qualified.

## System goal

CACE Studio is a modular scientific research environment in which an experiment is a typed graph of independently testable modules. The same experiment should be usable from the desktop Studio, the headless CLI, tests, and future external-agent integrations without changing the mathematical meaning of its results.

## Architectural layers

### 1. Experiment and module model

`cace_studio/core/graph.py` defines experiments as nodes and typed edges. Modules expose metadata, ports, parameters, execution and verification contracts. The module registry is the discoverability boundary used by the GUI and headless interfaces.

A module is responsible for its computation and local verifier. A module is not allowed to unilaterally promote itself to public formal evidence; canonical claim governance is applied after module verification.

### 2. Execution and evidence

`cace_studio/core/executor.py` validates the graph, orders execution, executes modules, collects verification records and creates run certificates. Verification states distinguish `PASS`, `FAIL` and `NOT_RUN`. Absence of executed verification is not success.

Evidence classes and software maturity are separate dimensions. Numerical, symbolic/exact, interval-certified and formally verified evidence must not be silently interchanged.

### 3. Claim and proof governance

`cace_studio/core/claim_registry.py`, `proof_ledger.py`, `formal_gate.py` and `qualification_drift.py` implement fail-closed formal promotion.

A module-level `FORMAL + PASS` survives into public run evidence only when the canonical claim registry and proof ledger agree on a qualified, content-addressed attestation and qualification-sensitive source has not drifted since the attested commit. See `docs/CLAIMS.md`.

### 4. Formal mathematics

`formal/cace_formal/` is the pinned Lean project. Lean proofs establish only the statements compiled under their explicit hypotheses and trusted foundational axioms. Formal workflow qualification additionally checks the pinned toolchain/dependency state, rejects unfinished proof tokens, builds the project, runs the kernel axiom audit and emits a content-addressed attestation.

Formal theorem qualification does not prove the Python/C++ application as a whole and does not imply production software maturity.

### 5. Native numerical runtime

`cpp/` contains C++20 components for computationally expensive kernels. Python remains the orchestration and research-integration layer. Native algorithms require independent tests and evidence appropriate to their numerical claims; speed never substitutes for correctness.

### 6. Studio GUI

`cace_studio/gui/` provides the visual scientific playground: module library, drag/drop graph editing, typed click-to-connect ports, parameter forms, execution, verification/proof views, reports and `.cace` experiment persistence. GUI convenience must not alter core evidence semantics.

### 7. Headless and agent interface

`cace_studio/cli.py` provides versioned JSON-oriented commands for tools and AI agents. `AGENTS.md` is the human/agent entry point. AI is optional and must not be part of the trusted computing base for executing or verifying an experiment.

Future generated repository indexes should expose module, claim, proof-dependency and source maps without duplicating canonical source by hand.

### 8. Plugins and local AI

Plugins are intended to follow a versioned SDK and explicit trust model. The planned local-AI provider layer will support no-code GUI discovery/configuration for providers such as Ollama and OpenAI-compatible local servers. AI suggestions may propose experiments or edits, but they cannot create mathematical evidence or set formal status.

### 9. Reproducibility and provenance

`.cace` experiments, run reports, certificates, dependency metadata and proof attestations should be deterministic or explicitly mark nondeterminism. CACE is moving toward content-addressed research bundles, signed attestations and an append-only transparency ledger. Optional external blockchain/timestamp anchoring is a provenance feature only; it never proves mathematical truth. See `docs/PROVENANCE_ATTESTATION.md`.

## Trusted-computing-base principle

For every promoted claim, CACE should make the trusted boundary inspectable: theorem source, Lean/kernel and allowed axioms, dependency pins, certificate checker, executable bridge, exact source commit, artifact digest and qualification workflow. Anything outside that boundary is context or evidence, not an implicit proof premise.

## Change discipline

Qualification-sensitive changes must trigger fresh formal qualification. Documentation, ordinary GUI presentation and canonical provenance-record acceptance may inherit an attestation only when the drift checker proves no qualification-sensitive source changed. New scientific capabilities should extend stable module/evidence contracts rather than create another version-specific wrapper unless a versioned boundary is genuinely required.


### 10. Browser-only gateway and hardened local service plane

The production browser is a presentation client, not a distributed CACE runtime.

Only the web gateway is public. The canonical computation/service plane remains
private/local:

```
browser
  -> public web gateway
     -> private orchestrator
        -> canonical scientific runtime
        -> native workers
        -> local AI broker
        -> account/protein store
        -> network/economy/payment brokers
        -> durable storage
        -> isolated proof runner
```

The gateway owns HTTP/session/input policy. Private services own privileged
capabilities. The browser never receives their credentials and never connects
directly to them.

This separation lets Base44, Gemini AI Studio, or another frontend builder
replace/improve the public webapp without becoming the authority for CACE
science, proof, wallets or host access.

See `CACE_DEPLOYMENT_BOUNDARY.json` and
`docs/WEBAPP_HARDENED_LOCAL_LAYER.md`.
