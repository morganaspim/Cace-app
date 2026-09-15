# CACE v3.33-v3.35 Gap Audit

Status: candidate implementation audit. This document is planning evidence only; it does not qualify software behavior or mathematical claims.

## v3.33 Studio UX

### Implemented/prepared in the candidate

- visual module drag/drop;
- click-output then click-input graph connections;
- typed port compatibility checks and one-source-per-input enforcement;
- movable/selectable nodes and selectable edges;
- rubber-band multi-select and select-all;
- delete selected nodes/edges;
- undo/redo snapshot history;
- internal graph-fragment copy/paste with fresh node IDs, parameter deep copies and internal-edge remapping;
- rollback-safe batch paste restoration;
- Align Left, Align Top, Align Vertical Column and Align Horizontal Row;
- Ctrl+wheel zoom, Fit Graph and Reset Zoom;
- module-library search/filter;
- parameter form editing;
- autosave and recovery;
- stale run-evidence invalidation after graph edits;
- Proof Explorer integration.

### Remaining before calling v3.33 complete

1. **Execution control:** run selected/subgraph with explicit upstream dependency semantics.
2. **Cancellation:** move long execution off the blocking GUI path and add safe cancel; pause only if modules/executor expose a valid checkpoint contract.
3. **Groups/subgraphs:** persistent visual/serialization model, not merely decorative rectangles.
4. **Units:** explicit quantity/unit contracts and connection validation rather than labels only.
5. **Minimap/large-graph navigation:** useful for substantial experiments.
6. **Additional layout tools:** optional distribute/grid/snap operations after core alignment qualification.
7. **GUI qualification:** automated Qt tests plus manual drag/connect/edit/run/save/open/recover/copy/paste/alignment smoke tests on supported platforms.
8. **Accessibility/usability pass:** keyboard navigation, focus behavior, errors and large-graph interaction.

Do not implement pause/cancel as superficial buttons around the current synchronous execution path; execution must first gain a real cancellation/checkpoint contract.

## v3.34 local AI

### Implemented/prepared in the candidate

- optional `AIProvider` abstraction;
- Ollama provider;
- OpenAI-compatible local provider;
- presets for LM Studio and llama.cpp;
- GUI configuration/health/model discovery;
- AI disabled by default;
- loopback-only `localhost`/literal loopback IP endpoint validation;
- credentials/query/fragment/path-traversal rejection;
- environment proxy bypass for local-AI requests;
- HTTP redirect refusal;
- AI output kept outside verification/certificate/proof-promotion semantics.

### Remaining before production qualification

1. exact-head provider/security tests on the consolidated candidate;
2. manual Ollama and at least one OpenAI-compatible local-server smoke test;
3. clear timeout/cancellation behavior in the UI for slow local models;
4. bounded prompt/context handling for very large experiments;
5. explicit privacy UX showing what experiment/run context is sent to the local model;
6. confirm AI-off operation has no model/server/network dependency;
7. future provider compatibility policy without weakening loopback/local-only default security.

## v3.35 module/plugin SDK

### Implemented/prepared in the candidate

- plugin API version `1.0`;
- versioned `plugin.toml` manifest;
- plugin ID validation;
- trust levels `builtin`, `trusted`, `untrusted`;
- untrusted execution refused by default;
- entrypoint containment inside the plugin directory;
- duplicate module IDs rejected by the core registry;
- missing/no-op registration rejected;
- **transactional registration:** plugins register into a staging registry first, so an exception after partial registration cannot mutate the live registry;
- built-in example plugin and SDK tests;
- documentation preserving the scientific evidence boundary.

### Remaining before production-grade third-party plugin distribution

1. stricter plugin-version compatibility/migration policy;
2. enforceable capability declarations rather than descriptive capability strings;
3. publisher/signing identity policy where appropriate;
4. isolated-process containment for untrusted/high-risk plugins;
5. resource/time/crash limits;
6. automated admission evidence for compatibility/security tests;
7. package-installed discovery and upgrade/downgrade tests;
8. explicit plugin API deprecation/migration policy.

Plugin trust never promotes scientific evidence. Formal claims remain subject to the canonical claim registry, proof ledger, exact formal qualification and drift gates.

## Priority before v3.37

These gaps do not all block v3.31 formal closure. The dependency order is:

1. restore self-hosted qualification infrastructure;
2. close v3.31 exact-head formal qualification;
3. run the consolidated v3.32-v3.36 regression/requalification wave;
4. fix candidate regressions and the canonical ledger-timestamp hardening gap;
5. finish the highest-value v3.33 execution-control pieces if needed for the certified FEM user workflow;
6. then start v3.37 Certified FEM/PDE.
