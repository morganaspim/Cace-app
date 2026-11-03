# Local AI Three-Model Architecture

This document replaces the generic local-AI plan for CACE.

The canonical local AI stack is:

- IBM Granite 3.3 2B Instruct: conversation, instruction following, intent routing, explanations, context management, and final user-facing responses.
- Phi-4-mini-reasoning: mathematics, scientific reasoning, geometric reasoning, experiment planning, symbolic reasoning, proof-obligation identification, and CACE tool planning.
- Qwen3.5-4B: visual and spatial reasoning over diagrams, meshes, coordinate-system images, plots, screenshots, geometry, and scientific visualizations.

Permanent mental model:

```text
Granite = communicates and routes
Phi     = reasons
Qwen    = sees
CACE    = computes, validates, certifies, and verifies
```

No AI model is scientific authority. No AI model may independently promote evidence, establish formal qualification, override graph validation, or turn a hypothesis into a verified CACE claim.

## Router

Implement `CaceAIRouter` as a structured router, not a free-form multi-agent chat. It should invoke the cheapest appropriate path:

- `CHAT`, `GENERAL_HELP`, `SUMMARIZATION`: Granite.
- `MATH_REASONING`, `SCIENTIFIC_REASONING`, `GEOMETRY_REASONING`, `GRAPH_CONSTRUCTION`, `GRAPH_REPAIR`, `TOOL_SELECTION`, `PROOF_OBLIGATION_ANALYSIS`, `RESEARCH_IDEA`, `BUILD_ON_CANVAS`: Phi.
- `IMAGE_ANALYSIS`, `MESH_ANALYSIS`, `PLOT_ANALYSIS`, `COORDINATE_ANALYSIS`: Qwen.
- `MULTIMODAL_SCIENCE`: Qwen structured observation -> Phi tool plan -> CACE validation/computation -> Granite explanation.

Do not run all models for every message.

## Provider Layer

Keep provider-neutral local inference:

- Ollama
- llama.cpp
- LM Studio / OpenAI-compatible local server
- compatible local inference runtime

The provider interface should support discovery, health checks, model listing, load/unload, chat, streaming chat, structured generation, cancellation, capabilities, and context metadata. Vision-capable requests must advertise that capability explicitly.

## Resource Modes

- `LIGHT`: Granite by default; Phi on demand; Qwen disabled or manually enabled.
- `STANDARD`: Granite available; Phi and Qwen available on demand.
- `RESEARCH`: Granite, Phi, and Qwen available with specialist cross-checking and CACE tool verification.
- `CUSTOM`: user chooses available models and loading policy.

Support always-loaded, load-on-demand, and unload-after-idle policies where practical.

## Structured Inter-Model Messages

Avoid uncontrolled natural-language loops between models. Prefer bounded typed records:

- Qwen -> Phi: `cace-visual-observation-v1`
- Phi -> CACE: `cace-tool-plan-v1`
- CACE -> Granite: `cace-result-summary-v1`

AI agreement is not verification. Specialist agreement may only prioritize candidate work for CACE checkers.

## Offline Network Boundary

The Granite/Phi/Qwen group operates in `LOCAL_ZERO_CONTACT` mode. The models may inspect structured local context and request schema-validated CACE tools, but they must not browse the internet or call remote services.

The GUI and backend may expose explicit user-facing API imports for scientific objects, such as AlphaFold protein metadata. These imports are allowed only as GUI/user actions or approved backend services. They are not unrestricted AI tools, and they do not give Granite, Phi, Qwen, or any symbiotic AI loop network access.

Qwen may see rendered canvas images and structured object state. Phi may reason over local equations, graph metadata, and proof obligations. Granite may explain local results. Canvas play by the AI group is gated by the user-facing `AI canvas play` option. When it is off, AI can suggest experiments in text but must not build or manipulate canvas geometry/algebra objects. When it is on, AI may propose local canvas edits, still without network access and still without evidence authority.
## Tool Access

Models do not receive unrestricted system access. Expose a typed tool registry with:

- tool id
- description
- input schema
- output schema
- permissions
- scientific authority level
- side-effect classification

Permission classes:

- `READ_ONLY`
- `COMPUTE`
- `PROPOSE_MUTATION`
- `USER_APPROVAL_REQUIRED`
- `FORBIDDEN_TO_AI`

AI-generated tool requests must be schema-validated before execution. AI must never modify canonical proof status, issue entitlements, access wallet secrets, modify production credentials, or bypass authorization.

## Context Builder

Do not dump the repository or workspace into every prompt. Build compact task context from:

- conversation summary
- current experiment
- selected nodes and graph neighborhood
- relevant capabilities
- latest execution/failure
- evidence and claims
- proof metadata
- coordinate state
- research idea state

## Geometry and Training Direction

Prepare for future adapters without changing the CACE architecture:

- `CACE-Phi-Geometry-Reasoner`
- `CACE-Qwen-Geometry-Vision`
- optional small coding model for local code assistance and tool authoring

CACE can generate validated synthetic datasets: exact objects, transformed representations, rendered images, tool traces, validated results, explanations, and evidence metadata across Cartesian, triangular/hex, complex, geometric algebra, mesh, visual, and typed-object representations.

Do not begin expensive fine-tuning before baseline benchmarks exist.

## Benchmarks Before Training

Measure Granite routing and explanation quality, Phi mathematical planning and invalid-graph rate, Qwen visual/spatial extraction quality, and end-to-end system validation success, latency, RAM/VRAM, model load time, cancellation, and failure recovery.

## UI Requirements

The Local AI UI should show:

- Assistant: IBM Granite 3.3 2B Instruct
- Scientific Reasoner: Phi-4-mini-reasoning
- Vision & Geometry: Qwen3.5-4B
- mode: Light / Standard / Research / Custom
- compute: CPU / GPU / Auto
- provider/model/load state/health/context/generation state
- optional routing trace for developer/research debugging

The routing trace is diagnostic only and is not evidence.

## Acceptance Tests

1. Granite chat: actual Granite inference responds to a simple CACE help prompt.
2. Route to Phi: finite-element Poisson error-estimation workflow request routes to Phi and yields a structured CACE workflow proposal.
3. Route to Qwen: mesh/geometry image routes to Qwen and returns structured observations.
4. Qwen -> Phi -> CACE: multimodal scientific task produces visual extraction, scientific plan, CACE validation/computation, then Granite explanation.
5. Simple chat does not wake every model.
6. AI OFF causes zero model calls.
7. Requests to mark unqualified results formally verified are refused and evidence remains unchanged.
8. Invalid AI-proposed graphs are rejected by CACE graph validation and cannot be overridden by AI.

## Implementation Priority

1. provider-neutral model runtime
2. Granite real chat
3. streaming and cancellation
4. router
5. Phi integration
6. structured Granite -> Phi handoff
7. Qwen integration
8. image/multimodal input
9. structured Qwen -> Phi handoff
10. CACE tool layer
11. AI context builder
12. experiment-aware conversation
13. graph proposals
14. Build on Canvas
15. Research mode
16. benchmarking
17. synthetic dataset generator architecture
18. later LoRA/fine-tuning

## Permanent Invariant

The three AI models are research assistants. They may observe, interpret, hypothesize, reason, plan, propose, explain, and request tools. They may not verify, certify, qualify, promote evidence, override authoritative computation, override graph validation, or alter canonical proof status.

Granite communicates. Phi reasons. Qwen sees. CACE decides what is computationally and evidentially established.
