# Local AI Model Selection

This is a practical model policy for the CACE local AI stack. It is not a proof artifact.

## Fixed CACE roles

- Granite communicates and routes.
- Phi reasons.
- Qwen sees geometry and visual structure.
- CACE computes, validates, certifies and verifies.

All models feel the canvas through typed heartbeat/perception packets. Heartbeat guides attention; it is not evidence.

## Recommended small coding model candidates

1. IBM Granite Code 3B Instruct
   - License: Apache 2.0.
   - Why: favorable enterprise/open license posture, small enough for local use, aligned with the Granite family already used for conversation.
   - Role: code edits, tool scaffolding, test generation, refactor proposals.

2. Qwen2.5-Coder 1.5B Instruct
   - License: Apache 2.0 for the exact 0.5B, 1.5B, 7B, 14B and 32B instruct sizes according to Apache Software Foundation tooling review.
   - Why: very small and often strong for local coding assistance.
   - Role: cheap iterative code proposal and small-tool synthesis.

3. Qwen2.5-Coder 7B Instruct
   - License: Apache 2.0 for the exact 7B instruct size.
   - Why: stronger coding ability while still plausible on local hardware with quantization.
   - Role: heavier rewrite proposals and multi-file planning.

Avoid making a coding model authoritative. Coding AI may propose source changes and tests, but CACE review, tests, Lean where applicable, and human/PR review decide what lands.

## Ranked optimization strategies for recursive improvement

1. Canonical tool traces before model training
   - Capture successful CACE graph proposals, validation failures, fixed graphs, execution results, and proof obligations.
   - Use traces to improve prompting, retrieval and benchmarks before fine-tuning.

2. Reasoning operator library
   - Promote recurring validated math operations into typed `ReasoningOperator` records with preconditions, invariants, inverse/composition metadata and checker links.

3. Proof-to-tool flywheel
   - When Lean verifies a reusable theorem, expose it through a deterministic CACE checker/tool.
   - Add GUI/toolbox affordances only after the evidence boundary is clear.

4. Cheap specialist routing
   - Granite handles ordinary chat.
   - Phi wakes for math/science/proof planning.
   - Qwen wakes for images, spatial structures and geometry.
   - Coding model wakes only for source/tool implementation tasks.

5. Geometry-first synthetic data
   - Generate exact geometric objects, transformations, rendered views, questions, tool traces and verified results.
   - Include multiple coordinate representations: Cartesian, polar, complex, hex/triangular, mesh, fractal and geometric algebra.

6. Benchmarks before fine-tuning
   - Measure invalid graph rate, proof-obligation identification, tool-call correctness, latency, memory and validation success.
   - Fine-tune only against measured failures.

7. Human/CI/Lean gates
   - RSI must not let AI mark its own changes verified.
   - All code and proof-tool upgrades go through tests, proof checks where applicable, and PR review.
